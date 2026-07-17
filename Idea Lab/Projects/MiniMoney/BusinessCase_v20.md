# Business Case: MiniMoney — v20

> Prepared by: Incubator. This revision responds to the Investment
> Committee's fourth review (`Verdict_v4.md`, "Proceed with Changes," six
> required changes plus a Gate Integrity observation) using the user's
> item-by-item decisions in `Clarifications_v20.md`. Authorized inputs for
> this cycle: `00_CaseStudy.md`, `BusinessCase_v16.md`, `BusinessCase_v18.md`,
> `Verdict_v4.md`, `Clarifications_v20.md`. Two things happen in this cycle,
> both from `Clarifications_v20.md`: (1) a **data-integrity fix**, not new
> content — Market & Competition is restored to its actual v16 high-water
> mark, having thinned across three cycles (fully restored v16 → bare
> cross-reference v17 → rebuilt from v17's thinned base at v18, because v16
> was not an authorized input that cycle); this directly instantiates
> Playbook Entries 5 and 6; and (2) resolution of all six of Verdict_v4's
> required changes plus the carried-over legal-citation closure from
> `Clarifications_v19.md` (resolved off-cycle, never yet incorporated into
> any Business Case revision — there is no `BusinessCase_v19.md`).

## What Changed in v20 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**1. Market & Competition — data-integrity restoration (not a new
decision).** Restored in full from `BusinessCase_v16.md`'s actual text —
population-base derivation (Stats SA), device-access study (Stellenbosch),
OS split (Statcounter), the full reachable-market funnel derivation, all
three named competitors in full detail, and the international comparables
(GoHenry/Greenlight/FamZoo/Bomad) — rather than re-derived from v18's
thinner, v17-sourced reconstruction. **This does not change the section's
Confidence or Evidence tags**, stated explicitly per this cycle's
instruction: v18's condensed version already carried the same underlying
evidence tiers (the SARB/Stellenbosch figures, the [Guessing]-tagged
adoption/conversion estimates) — what's restored is derivation detail and
traceability, not a new evidentiary tier. Confidence remains Medium,
Evidence remains Supported, exactly as both v16 and v18 held it. **One
genuine residual gap surfaced by this restoration, named rather than
smoothed over:** v16's population-base derivation was computed at the
*child* level (≈14-15M children aged 6-18), while v18's funnel-unit
correction (`Clarifications_v18.md`) resolved the funnel's *unit* to be
the family. No separate family-level re-derivation from the population
base exists — the 18,000-61,000 install range is applied as a
family-level figure by convention, not because the population math was
redone at the family level. This is a new item in Outstanding Questions,
not a resolved one.

**2. Legal citation closure (carried from `Clarifications_v19.md`,
incorporated into a Business Case for the first time).** The retained
lawyer has confirmed both the pinpoint reference (*Conradie v Rossouw*
1919 AD 279, Appellate Division) and the substantive proposition (animus
contrahendi as the touchstone of South African contract formation). This
closes Critical Gap #8 outright — not merely elevates it, as
`Verdict_v4.md` required change #6 asked.

**3. All six `Verdict_v4.md` required changes, resolved:**

- **Acquisition/CAC (required change 1): organic-only, zero paid
  acquisition.** No marketing budget allocated from the R10,000 total.
- **Runway-slippage contingency (required change 2): self-fund further.**
  If month 6 arrives without secured funding, or any workstream slips,
  the user's decision is to personally extend the runway rather than
  pause or close. **Directional, not costed** — no specific additional
  amount or maximum extension period is specified, and none is invented
  here.
- **Exam-bonus motivation-risk instrumentation (required change 3):
  Incubator-drafted candidate lightweight motivation-probe** (parent- and
  child-facing), added to the adopted pilot measurement package at
  near-zero marginal cost. Tagged Evidence: Assumed — not yet reviewed by
  the child-development specialist who designed the rest of the pilot
  package; that review is flagged as a recommended next step, not a
  completed one.
- **Curriculum authorship (required change 4): EXPLICITLY OPEN, not
  guessed.** The user has not decided between authoring personally or
  engaging a designer via the zero-marginal-cost advice policy, pending
  confirmation that policy's scope extends to instructional-design
  expertise. Documented as a named, pending decision — distinct from
  every other item in this clarification, which is resolved.
- **Minimal data-breach/incident-response commitment (required change 5):
  Incubator-drafted candidate**, founder-authored, added to Constraints.
  Tagged Evidence: Assumed; specialist (Data-Privacy Practitioner) review
  flagged as advisable before finalization, though not required to close
  this Investment Committee item.

**4. Gate Integrity follow-up.** `Verdict_v4.md` flagged two
self-certification bullets (expert roster, Devil's Advocate) as
"technically present, not substantively demonstrated in-document." This
cycle's Self-Certification section below reproduces a concrete excerpt
from each, addressing the observed pattern directly rather than leaving
it as a bare pointer again.

**The Readiness Score is unchanged at 70.0% (91/130).** Per Playbook
Entry 1, stated explicitly: the changes this cycle are predominantly
decisions and an evidentiary restoration, not new information closing a
Partial section's own independent gaps. Full accounting in the Readiness
Score section below.

## Executive Summary

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18), launching first in
South Africa on Android (iOS porting planned as future work), combining
gamified task assignment with a simulated payroll system. The parent
submits a budget setting the minor's "basic income"; tasks earn Mbucks (a
real-money-pegged in-app currency, e.g. 10 Mbucks = R10) which accumulate
into a "payslip," while every completed task separately earns a fixed 10
Mpoints — a distinct, non-monetary cosmetic-store currency. The parent
receives an invoice and pays the owed amount directly to the child via
the parent's own banking app — MiniMoney itself never holds, transmits,
or takes custody of funds. Subscription pricing is R59.99/month, covering
up to 4 children per family account; the funnel and revenue unit is the
family (one subscription = one family = up to 4 children). Monetization
is subscription-only at launch, with advertising deferred to a possible
post-launch V2. **Growth is organic-only at launch — zero paid
acquisition, no marketing budget allocated** (decided this cycle). The
late-payment penalty mechanic is incurred entirely by the parent (5→6→7
Mbucks/week, pilot cap 3); the child has zero visibility into it, and a
grace-period/pre-escalation reminder mechanism reduces trigger frequency
at the source. The exam-period bonus is a user-defined hybrid: primary
rewards for controllable behaviors (study time, homework completion),
with a secondary bonus retained for improved results — a deliberate
partial adoption of specialist recommendation carrying a known, accepted
residual intrinsic-motivation risk, **now paired with an Incubator-drafted
candidate qualitative motivation-probe** added to the pilot's measurement
package (Evidence: Assumed, pending specialist review). A distinct,
15-18-only curriculum element, "Fintech Advance," teaches the concepts of
trending/entrepreneurial ventures (forex trading, dropshipping) with no
in-app trading execution, gated by a separate explicit parent opt-in, and
does not use the product's own Mpoints/badge gamification for its
content.

**This cycle's central development:** all six of the Investment
Committee's required changes are resolved by direct user decision or
Incubator-drafted candidate content per explicit instruction, and one
carried-over legal item is closed. The acquisition mechanism is now named
(organic-only). A runway-slippage contingency exists (self-fund further —
directional, not costed). The exam-bonus motivation-risk gap has a
candidate instrument, pending specialist review. Curriculum authorship is
documented as an explicit, named open decision, not resolved and not
guessed. A minimal data-breach/incident-response commitment now exists as
a founder-authored candidate, pending specialist review. The Conradie v
Rossouw citation — the case's self-described strongest legal position's
one open dependency — is now fully verified. **Separately, Market &
Competition is restored to its actual, fuller v16 content this cycle**
(a data-integrity fix, not new information — see What Changed in v20).

**The case's financial picture remains thin by design**, now with two
material decisions layered on: R10,000 total development budget,
professional opinions at zero marginal cost, a 6-month runway before
external funding is needed, **zero paid acquisition spend**, and **a
directional (uncosted) self-fund-further commitment if the runway slips
or month 6 arrives unfunded.** The binding constraint remains the 6-month
runway containing build, parallel curriculum authoring, pilot
instrumentation and execution, and two personally-owned regulatory
rechecks, executed substantially by one person — named as the case's
execution-capacity risk, now with a stated (if uncosted) contingency
rather than none at all.

**The Readiness Score holds at 70.0% (91/130), clearing the completion
gate's ≥70% threshold with no margin.** This cycle's changes are
predominantly decisions and an evidentiary restoration rather than new
information closing independently-Partial sections' own gaps — detailed
in the Readiness Score section.

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
personal-device ownership by age 10, per a 2024 Stellenbosch-region study
of five former Model C high schools, Grade 4-11).

A first-party interview round (n=10 families) found 6 of 10 confirmed
interest in using the app and stated willingness to pay for it; 7 of 10
expressed interest specifically in the education aspect. This is
genuine, first-party, MiniMoney-specific evidence, categorically
different from comparable-market inference, but it is not statistically
significant. Per a standing instruction adopted at v9 and reaffirmed at
v10, this data point must not be used as if it were a representative or
validated demand signal until superseded by the planned 20-50 family
pilot or a structured survey.

Unchanged this cycle: the pilot remains the vehicle for a demand read
(see Validation Strategy), directional and qualitative per the
child-development reviewer's underpowering caution. Status remains
Partial for the same reason it has since v8: there is a real,
encouraging, directional signal, but still no established finding that
parents broadly perceive this as a problem worth paying to solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model. No direct South African incumbent does what
MiniMoney does. Restored this cycle (see Market & Competition): the
richer competitive detail, the reachable-market funnel derivation, and
international comparables (GoHenry, Greenlight, FamZoo, Bomad) confirming
MiniMoney's non-custodial, track-only model has structural precedent
elsewhere and is not a category outlier.

The subscription price (R59.99/month, up to 4 children per family)
sharpens the competitive read against MoneyTime SA's R995/year (25%
sibling discount): MiniMoney's annualized price (R719.88/family/year)
sits below MoneyTime SA's rate even before the sibling discount —
relevant opportunity context, but this does not on its own establish
market size or demand, which remains governed by the same n=10,
non-representative bound described in Problem. **Growth is now decided
as organic-only** (see Revenue & Costs, Financial Considerations); the
schools-partnership channel — the strongest demonstrated reach model in
the category — remains named but still has no timeline, target, or
resourcing plan (Outstanding Questions). Status remains Partial: the
differentiation thesis is coherent and partly evidenced, but no
structured market-sizing or validated demand study has been conducted.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam-period bonus (hybrid: behavior-primary rewards plus a retained
secondary results bonus) → invoice/payslip → payment confirmation with
escalating late-penalty (grace-period/pre-escalation reminder mechanism
committed) → age-gated education. The late-penalty step is incurred
entirely by the parent and is invisible to the child.

**Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
payment loop, including the dispute and late-penalty mechanics, with a
small pilot cohort of South African families (candidate target: 20-50
families) before wider release. The pilot formally adopts the specialist
pilot-measurement package (see Success Criteria) plus this cycle's
candidate motivation-probe addition, and serves double duty: mechanic-
safety signal AND a directional demand read (see Validation Strategy).

**Growth (6-12 months):** validate the subscription-conversion assumption
against the 1-3% subscription-only reference range; validate curriculum
engagement as a leading indicator of retention; evaluate iOS port timing
based on Android traction.

The 90-day (15,000 installs) vs. annual funnel (18,000-61,000 installs)
target tension remains resolved via `Clarifications_v10.md`. All install
and subscriber figures are per-family. Status remains Complete: every
tension previously flagged in this section is resolved by direct,
Verified-tier user clarification.

## Success Criteria

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Core criteria, carried from v8/v9: pilot success (majority of families
complete ≥4 consecutive weekly cycles); curriculum engagement (30%, no
external benchmark); operational health (65% task-completion without
dispute, no external benchmark); freemium/subscription conversion (2%,
benchmarked against the 1-3% subscription-only range); retention (no
figure proposed). The curriculum-engagement, operational-health, and
retention criteria remain unbenchmarked.

**Family-relationship-strain criterion — measurement package adopted into
pilot design** (`ChildDevelopmentReview_v1.md`): borrowed items from the
Parenting Stress Index – Short Form and the Family Assessment Device –
General Functioning Scale, administered to parents at baseline and
partway through the pilot; within-family, within-week correlation
tracking (late-penalty events vs. reported household tension);
age-stratified results (6-9, 10-14, 15-18 bands); a brief child-report
instrument (abbreviated Child–Parent Relationship Scale, Conflicts
subscale). The reviewer's explicit caution stands: 20-50 families is not
large enough for full validated-instrument statistical power; these are
for lightweight, qualitative early-warning signal detection.

**Exam-bonus motivation-risk instrumentation — Incubator-drafted
candidate addition, this cycle (per `Verdict_v4.md` required change 3 and
`Clarifications_v20.md`).** The measurement gap previously named — the
adopted package targets family stress, not motivation — now has a
candidate probe, designed as a natural extension of the existing
instruments rather than a separate study:

- **Parent-facing:** 2-3 short items administered alongside the existing
  PSI-SF/FAD-GFS timepoints (baseline, mid-pilot) — e.g. a Likert item
  ("My child seems to complete tasks mainly to earn the exam bonus,
  rather than because the task itself matters") plus one open-ended
  prompt inviting the parent to describe what seems to motivate their
  child's task completion during exam periods specifically.
- **Child-facing (age-appropriate, abbreviated):** administered alongside
  the existing Child–Parent Relationship Scale timepoint — for the
  10-18 bands, a brief forced-choice/open item distinguishing
  behavior-oriented from bonus-oriented framing ("why do you do your
  tasks?"); for the 6-9 band, a simplified picture- or simple-
  language-based variant consistent with the age-band framework.
- **Cost and timing:** near-zero marginal cost — administered at the same
  survey events as the already-adopted instruments, not a separate
  measurement wave.
- **Evidence: Assumed.** This is an Incubator-drafted candidate, not yet
  reviewed by the child-development specialist (Expert Roster Entry 2,
  author of `ChildDevelopmentReview_v1.md`) who designed the rest of the
  adopted pilot package. **That specialist's review is flagged as a
  recommended next step, not a completed step** — the probe should not be
  treated as validated instrument design until reviewed.

The underlying substantive risk remains confirmed, not resolved: the
late-penalty redesign narrows but does not eliminate the Family Stress
Model's affective pathway, and the exam-bonus hybrid's residual
intrinsic-motivation risk is now candidate-instrumented but not yet
specialist-reviewed or adopted.

Status remains Partial: the relationship-strain criterion has an adopted,
specialist-designed measurement plan; the motivation-risk gap now has a
candidate (not yet specialist-reviewed) instrument; curriculum
engagement, operational health, and retention remain unbenchmarked.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18;
parents/guardians as sole registration custodian and subscription
purchaser; the app operator (a solopreneur founder); the South African
Information Regulator and the Advertising Regulatory Board; three named
competitor/adjacent-market stakeholders — African Bank's MyWORLD Power
Pocket, MoneyAfrica Kids, MoneyTime SA; Apple/Google as app-store
platform stakeholders.

Two regulator stakeholders remain, each owned by the user personally at
build-spec stage with a decided launch fallback: the South African
Reserve Bank (SARB) and the Payments Association of South Africa (PASA),
via the National Payment System Act, engaged by the optional
account-linking feature's open-banking question (fallback: launch without
account-linking); and the Film and Publication Board (FPB), via the Films
and Publications Amendment Act 2019, of uncertain but plausible
application to the Mpoints gamified rewards system (fallback: launch
without Mpoints, ripple effects traced in Legal & Compliance).

The linking aggregator (Stitch/Mono-style, where a parent opts in)
remains an additional data-processor stakeholder. **The retained legal
counsel's open action is now closed**: the Conradie v Rossouw citation is
verified (pinpoint reference and substantive proposition both confirmed
this cycle). **The retained child-development professional (Expert
Roster Entry 2) is flagged as a recommended-next-step reviewer for the
new candidate motivation-probe**, not yet engaged for that specific
review. **A Data-Privacy Practitioner (Expert Roster Entry 5) is
similarly flagged as advisable for reviewing the new candidate
data-breach/incident-response commitment**, though not required to close
this cycle's Investment Committee item. A future AI mediator feature for
dispute resolution remains explicitly out of current scope.

Status remains Partial: both regulator stakeholders now have an owned
recheck and a fallback, but their specific obligations remain unresolved
pending those rechecks; the two named specialist reviews above are
recommended, not yet engaged.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens 6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18, and their
parents/guardians, in South Africa, on Android at launch (iOS deferred).
A minor is not an independently reachable user: every child account
requires a parent acting as registration custodian from the outset. The
paying customer unit is the family (one subscription = one family = up
to 4 children) — the child is the user, the parent is the customer, and
all funnel counts are family counts. Status remains Partial: the target
population is clearly named and the customer unit is unambiguous, but no
market-sizing or persona-level detail exists beyond Market & Competition
and the funnel figures in Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The Free/Subscription feature split, the R59.99/month (up to 4 children
per family) price, and the full Fintech Advance description stand as
restored at v16 and carried through v18. Constraints and decisions
attached:

**Mbucks non-transferability — a locked product-spec constraint.** Per
`LegalOpinion_v1.md` Q1, MiniMoney's low money-transmitter/e-money risk
is contingent on Mbucks remaining a pure unit-of-account. Any future
roadmap change to this requires the money-transmitter analysis to be
redone (see Legal & Compliance, Business Model, Constraints).

**Fintech Advance mitigation — adopted.** The module does not use
MiniMoney's existing Mpoints/badge gamification for the trading-education
content itself, and its presentation leans toward risk literacy rather
than aspirational framing, per `ChildDevelopmentReview_v1.md` Q5.

**Terminology — adopted.** Debt-coded language ("invoice," "arrears,"
"late penalty") is reserved for parent-facing surfaces only; child-facing
surfaces use softer language.

**Conditional exposure, named not hidden:** under the no-Mpoints launch
fallback (see Legal & Compliance), the in-app cosmetic store has no
currency and must be removed from that configuration, thinning the
subscription tier's child-facing appeal. The value proposition as
specified is complete for the primary configuration; the fallback
configuration's feature-table variant is a named conditional design item
(Outstanding Questions).

Status remains Complete: price, feature boundaries, and all previously-
pending decisions within this section's scope are made; the fallback
variant is an explicitly tracked conditional, not an unmade decision.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

> **Provenance note (Playbook Entries 5 & 6) — data-integrity restoration,
> this cycle.** This section thinned across three consecutive cycles:
> fully restored at v16 (population-base derivation, device/OS/SARB data,
> international comparables, all three competitors in full detail);
> reduced to a bare cross-reference to v16 at v17; then rebuilt at v18
> from only v17's already-thinned cross-reference content, because v16
> was not among that cycle's authorized inputs — v18's own provenance note
> said as much. This cycle's delegation explicitly includes
> `BusinessCase_v16.md`, so the section below is restored directly from
> v16's actual text, not re-derived from v18's thinner base. **This is a
> completeness fix, not new case content, and — stated explicitly per this
> cycle's instruction — it does not change this section's Confidence or
> Evidence tags.** The evidentiary tiers restored below ([Certain]-tagged
> Stats SA and Statcounter figures, [Likely]-tagged SARB and device-study
> figures, [Guessing]-tagged adoption/conversion extrapolations) were
> already reflected, in condensed form, in v18's shorter version; what's
> restored is derivation detail and traceability, not a new evidentiary
> tier. Confidence remains Medium, Evidence remains Supported, as both v16
> and v18 independently held.

**Population base (6-18):** [Certain] Stats SA's mid-2025 estimate puts
South Africa's total population at 63.1 million, with children under 15
at 26.2% (≈16.5 million). [Guessing] Stats SA does not publish a clean
6-18 breakout; extrapolating from single-year cohort size (~1.1M/year
under 15) and adding the 15-18 band gives a modeled estimate of roughly
**14-15 million people aged 6-18** — not a directly sourced figure.

**Device access:** [Likely] A 2024 South Africa-specific study (five
former Model C high schools, Stellenbosch research) found 62% of learners
Grade 4-11 own a personal device by age 10, and 83% have a social media
account by age 12. This is personal ownership, not household access;
broader household access is plausibly 75-85% for the 6-18 band, a bounded
guess, not a stat.

**OS split:** [Certain] Android holds 76.74% of mobile OS share in South
Africa as of May 2026 (Statcounter), iOS 23.24%. This is traffic share,
not population share, but is a reasonable proxy indicating an
Android-first launch reaches the large majority of the reachable market.

**Parent financial-app engagement (the real gate):** [Likely] SARB's
Payments Study (SCPC/DCPC, 2023, adults 18+, national population base
40.5M) found 50.3% of South African adults use banking apps regularly.
[Guessing] Parents of school-age kids skew toward the economically active
25-54 bracket, more banked/app-literate than the national average — a
reasonable adjustment is **55-65% banking-app engagement** for this
specific parent cohort.

**Reachable-market funnel (population-level derivation):** 14.5M kids ×
~70% device access × ~60% parent digital-financial engagement ≈ **6.1M
kids in "reachable" households** (device present, parent already
comfortable transacting digitally) — the realistic Serviceable
Addressable Market, not the ~14.5M Total Addressable Market.

**Adoption rate (the least-evidenced figure in the chain):** [Guessing]
No public South African benchmark exists for kids'-financial-education-
app adoption specifically — confirmed unclosable by further desk research
(`ResearchFindings_v1.md` Item 1); inference from adjacent markets
(GoHenry/Greenlight UK/US): a new entrant with no bank/school
distribution typically captures 0.3-1% of its reachable pool as installs
in year one. Free-to-paid conversion for freemium/subscription
kids'-finance apps benchmarks 2-6% globally; South Africa's lower
discretionary income argues for the low end — **1-3%**, the range
applicable given the subscription-only monetization decision.

**Rerun funnel:** ≈6.1M reachable kids × 0.3-1% Year-1 install capture ≈
**18,000-61,000 free installs**. **Funnel-unit reconciliation (per v18's
resolution, `Clarifications_v18.md`): this range is applied as the
family-account install count**, not a per-child count — one install-unit
= one family = up to 4 children. Applying the 1-3% subscription-only
conversion range: **180-1,830 paying families in Year 1.** The
alternative 360-2,440 range cited in earlier versions is retired (derived
under the superseded 2-4% ads-hybrid assumption); all revenue statements
in this document use 180-1,830 exclusively.

**Named residual gap, not smoothed over:** the population-base derivation
above (14-15M children) is computed at the *child* level; there is no
separate family-level re-derivation of the reachable market that accounts
for the up-to-4-children-per-family cap. The 18,000-61,000 range is
applied at the family level by the v18 funnel-unit decision, not because
the underlying population math was redone at the family level — the
average children-per-family distribution remains unknown (see
Assumptions), so the true relationship between the child-level reachable
population and a family-level install count is unquantified. This is a
new item in Outstanding Questions this cycle.

**Competition in South Africa specifically:** no direct incumbent does
exactly what MiniMoney does (gamified, standalone, mobile-native,
direct-to-parent-distribution consumer app). **Three named local
players**, each missing at least one defining dimension:

- **African Bank's MyWORLD Power Pocket** — kids' sub-accounts with debit
  cards under a parent account; a banking feature, not education-led;
  confirmed to carry no monthly fee (a free sub-account add-on), setting
  a "zero price" anchor in the same market for a banking-feature
  alternative.
- **MoneyAfrica Kids** — Nigerian-origin edtech app, courses/quizzes,
  parent-subscribes-child model; available but not built for South
  Africa; shows 10,000+ Google Play downloads and 3,000+ Apple downloads
  (pan-African, not SA-specific); its premium price remains
  unpublished/unknown.
- **MoneyTime SA** — web-based financial literacy curriculum, ages 10-15,
  sold B2B2C through schools at R995/year (25% sibling discount); claims
  over 1,500 schools and 130,000 students reached (self-published, not
  independently audited) — the strongest demonstrated reach model in the
  category, still with no timeline, target, or resourcing plan for
  MiniMoney's own schools-partnership channel (see Outstanding
  Questions).

None combine gamification + mobile-native + direct-to-parent distribution
the way GoHenry/Greenlight do in the US/UK — a real, evidenced gap — but
it also means there is no local comparable data to validate
willingness-to-pay against.

**International comparables** (`ResearchFindings_v2.md` Item 3) split
into two structurally different approaches. **GoHenry** (recently folded
into Acorns Early) and **Greenlight** solve payment-verification by
becoming the money-mover themselves — issuing their own prepaid card and
holding/moving funds under card-issuing/e-money licensing, a materially
different regulatory posture than MiniMoney's deliberately non-custodial
design. **FamZoo** (IOU-accounts feature) and **Bomad** ("Bank of Mom and
Dad") are closer structural analogs: both are track-only, honor-system
products with no bank integration, confirming MiniMoney's chosen model
has precedent elsewhere and is not a category outlier. No
South-Africa-specific comparable to FamZoo or Bomad was found.

**What remains unresearched:** validated demand (n=10 bound still
governs; the pilot's demand read will be directional only); structured
market sizing beyond the user's own funnel estimate; MoneyAfrica Kids'
premium price; the schools-partnership channel's timeline, target, and
resourcing; **acquisition economics against the now-decided organic-only
growth strategy** (see Revenue & Costs) — whether organic discovery alone
can plausibly reach the funnel's own 18,000-61,000 range is untested.

Status remains Partial: the competitive landscape and funnel are fully
documented with derivation detail restored, and the unit ambiguity is
resolved, but the most decision-relevant figures (Year-1 adoption,
conversion rate) remain the user's own labeled lowest-confidence
estimates, unvalidated, and the child-to-family population conversion is
now a named, unresolved gap.

## Business Model

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Subscription-only at launch, ads deferred to V2; R59.99/month per family,
covering up to 4 children — the family is the revenue unit. MiniMoney is
a facilitation/education layer that sits on top of the parent's own bank
account and does not move or hold funds.

The core business-model uncertainty flagged since v8 — money-transmitter
licensing — remains resolved per `LegalOpinion_v1.md` Q1: risk is low,
contingent on Mbucks remaining strictly non-transferable and
non-redeemable.

Optional account-linking remains a trust/verification feature within the
existing subscription model. Its NCR question is resolved clean; the
SARB/NPS Act open-banking question remains genuinely unsettled, owned by
the user personally, timed to build-spec stage, with an explicit
fallback: launch without account-linking. If pursued post-launch,
advertising remains framed as a partial CAC-offset lever, not a
standalone revenue pillar — now more clearly so given the organic-only
launch decision (see Revenue & Costs).

The FPB classification question carries an explicit launch fallback
(launch without Mpoints); the Mpoints/Apple IAP-currency question is
mooted entirely under the no-Mpoints fallback. Status remains Complete:
the model's structure, unit, price, and every put-to-decision item within
its scope are decided; the remaining opens are externally-gated rechecks
with owner and fallback.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Revenue (per-family).** Subscription revenue at R59.99/month per family
against the corrected Year-1 range of **180 to 1,830 paying families**
(see Market & Competition):

- Lower bound: 180 families ≈ **R10,798/month** (≈ R129,578/year
  run-rate).
- Upper bound: 1,830 families ≈ **R109,782/month** (≈ R1,317,380/year
  run-rate).
- These are end-state run-rates against an unvalidated funnel and an
  unvalidated conversion rate; actual Year-1 collected revenue would be
  ramp-dependent and lower.

**Costs.**

- **Development budget: R10,000 total** committed for the app build.
- **Professional opinions/advice: zero marginal cost to the venture**,
  via the user's existing policy (scope/usage limits undocumented — a
  minor named open item).
- **Runway: 6 months** at current commitment before external funding is
  needed.
- **Acquisition/CAC — DECIDED this cycle (`Verdict_v4.md` required change
  1, `Clarifications_v20.md`): organic-only, zero paid acquisition.** No
  marketing budget is allocated from the R10,000 total. Growth relies on
  word of mouth, the schools-partnership channel (still itself lacking a
  timeline/target — see Outstanding Questions), and organic app-store
  discovery. **This closes the previously-named "still open" item — no
  CAC estimate or marketing budget exists — as a made decision (zero),
  not an unaddressed gap**, though whether organic-only growth can
  plausibly reach the funnel's own 18,000-61,000 range remains untested
  (see Market & Competition).

**Reconciliation against the prior agency reference range, stated
plainly:** the previously-cited $25,000-$120,000+ engineering-cost range
was a reference frame, not the plan. R10,000 is roughly $550, i.e. 45× to
220× below the agency range's bounds. The budget is only coherent because
it prices in the founder's own unpaid labor plus AI-assisted development.
**R10,000 buys days, not months, of professional engineering if the
founder's own capacity fails — there is no buffer to purchase execution.**
This is the case's execution-capacity risk, now with a directional
contingency (self-fund further — see Financial Considerations,
Constraints) rather than none at all.

**Still open:** curriculum content production cost is unpriced (the
workstream is committed, its cost is not); no post-runway funding ask is
sized. Status remains Partial: the acquisition-mechanism gap is now
closed by decision, but the revenue side rests on unvalidated estimates
and the cost side still lacks content-production and funding-ask figures.
Per Playbook Entry 7, this section is deliberately NOT raised to Complete
on the momentum of this cycle's resolution — its own remaining named
opens (content cost, funding ask) are untouched by it.

## Operations

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

Core mechanics (budget and earning, task structure,
completion/verification/reporting flow, dispute mechanism, payment
confirmation, late-penalty parent-only design) are unchanged in
structure. All specialist design decisions from prior cycles stand:
exam-period bonus as a hybrid (primary reward for controllable behaviors,
secondary bonus retained for improved results, with a known, accepted
residual intrinsic-motivation risk — **now candidate-instrumented, see
Success Criteria**); late-penalty grace-period/pre-escalation reminder
mechanism; Fintech Advance gamification-avoidance.

**New build-spec items introduced by the hybrid bonus, unchanged:** the
mechanism for logging/verifying the behavior inputs and the grade-input
mechanism for the retained results-bonus layer both need specification at
build time.

**Known operational gap, tracked:** dispute-escalation beyond the
48-hour window has no formal resolution mechanism.

Status remains Complete: every specialist recommendation within this
section's scope has a recorded decision; remaining opens are build-spec
parameters and a tracked edge-case mechanism, not undecided
recommendations.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v18. Still unspecified: how account-linking is technically
initiated; how payment confirmation is captured beyond the accept/dispute
UI; the exam-bonus grade-input mechanism; the hybrid bonus's behavior-
input logging/verification mechanism; the grace-period/reminder
notification infrastructure. Status remains Partial.

## Legal & Compliance ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The retained specialist legal opinion (`LegalOpinion_v1.md`) remains the
Verified-tier foundation of this section — all seven originally-scoped
questions answered.

**1. Money-transmitter/payment-facilitation risk: low, contingent on a
locked product-spec constraint.** [Likely] This holds only as long as
Mbucks cannot be spent, transferred, or redeemed anywhere other than
through the parent's independent banking-app payment — confirmed
[Certain] against SARB's e-money Position Paper. Courts look at
substance, not labels (*Maize Board v Jackson* 2005 (6) SA 592 (SCA)).
The NCR's Payment Distribution Agent category is confirmed inapplicable.

**2. Universal parental-consent gate: legally sufficient as designed,
with two hardening recommendations.** POPIA s34/s35(1)(a) is satisfied by
the current universal, no-carve-out consent gate. Two hardening
recommendations, not yet built: consent-flow documentation separation;
lightweight parent identity-verification step.

**3. POPIA Section 14 retention:** confirmed [Certain] no minor-specific
supplementary rule exists; a specific retention purpose, period, and
deletion trigger must be affirmatively designed and documented.

**4. Minor contractual capacity: the case's strongest legal position —
now fully verified.** The "rights without obligations" minor-contract
exception fits MiniMoney's structure, with the parent's obligation better
characterized as a unilateral undertaking or conditional donation,
sidestepping the domestic-agreement-presumption question via animus
contrahendi doctrine (*Pitout v North Cape Livestock* 1977). **The
supporting citation — the Conradie v Rossouw pinpoint reference — is now
CLOSED this cycle** (`Clarifications_v19.md`, incorporated for the first
time here per `Clarifications_v20.md`): the retained lawyer has confirmed
both the pinpoint reference (*Conradie v Rossouw* 1919 AD 279, Appellate
Division) and the substantive proposition (animus contrahendi as the
touchstone of South African contract formation). This item is fully
resolved — no longer a pending external action, and the underlying
citation requirement `Verdict_v4.md` asked to be treated as a "hard,
non-negotiable gate before any public or marketing use" is satisfied.

**5. Terminology risk: real, the single highest-optics-risk item in the
case — mitigation ADOPTED.** ARB Code Clause 14.2 and Clause 6.1, Section
III are both engaged, plus a CPA secondary layer; no ARB ruling addresses
this fact pattern, so MiniMoney would be a natural first test case if
challenged. Debt-coded terminology is reserved for parent-facing surfaces
only.

**6. SARB/NPS Act open-banking question (account-linking) — owned,
timed, with fallback.** NCR registration is confirmed inapplicable
[Certain]; the SARB question remains genuinely unsettled. Owner: the user
personally; timing: build-spec stage; fallback: launch without
account-linking.

**7. FPB classification question (Mpoints) — owned, timed, with fallback
and full ripple-effect trace.** The Films and Publications Amendment Act
11 of 2019 gives the FPB a classification mandate over "interactive
computer games"; whether the Mpoints mechanic is caught is genuinely
fact-specific. Owner: the user personally; timing: build-spec stage;
fallback: launch without Mpoints.

**No-Mpoints launch configuration — ripple-effect trace, unchanged:** the
in-app cosmetic store is removed; the flat 10-Mpoints-per-task reward is
gone (weakening the 6-9 tier's immediate-feedback loop); the Google Play
loyalty-point disclosure item is mooted in that configuration; Fintech
Advance's gamification-avoidance decision is trivially satisfied; the
badge-residual check within the FPB recheck remains a named open item.

**Status remains Complete.** All seven originally-scoped questions are
answered at Verified tier; the two unsettled external regulatory
questions are pending external rechecks with named owners and decided
fallbacks. **The one previously-unverified citation is now fully closed**
— no open legal action remains in this section.

## Risks

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

All previously-identified risk categories remain catalogued; decision
status updated per this cycle's changes.

- **Regulatory risk:** core invoice/payment-trigger/late-penalty
  mechanic assessed low-risk by retained counsel. Two narrower open
  regulatory questions (SARB/NPS Act, FPB) each carry a named owner,
  timing trigger, and decided fallback. Residual: the questions
  themselves remain externally unsettled until the rechecks run.
- **Execution-capacity risk — now with a stated (uncosted) contingency.**
  A solopreneur venture with a R10,000 total development budget, a
  ~3-month directional build timeline, a parallel curriculum-authoring
  workstream, an instrumented 20-50 family pilot, and two personally-
  owned regulatory rechecks — all inside a 6-month runway, executed
  substantially by one person, with no cash buffer to purchase external
  engineering if founder capacity fails. **This cycle: if month 6 arrives
  without secured funding, or any workstream slips, the user's decision
  is to self-fund further rather than pause or close — directional, not
  costed.** This reduces the risk of an uncontrolled stop but does not
  reduce the underlying resourcing tightness, and introduces an
  unquantified personal-financial-exposure dimension to the founder's own
  risk profile.
- **Acquisition/adoption risk — sharpened this cycle.** Zero paid
  acquisition is now the decided strategy against an 18,000-61,000
  family-install funnel; whether organic discovery, word of mouth, and an
  unresourced schools-partnership channel can plausibly reach this range
  is untested and not benchmarked anywhere in the case.
- **Child-safety/data-privacy risk:** consent model confirmed legally
  sufficient as designed; two hardening recommendations remain build
  tasks. POPIA Section 14 retention policy remains an affirmative design
  requirement. **A minimal data-breach/incident-response commitment now
  exists as an Incubator-drafted candidate (see Constraints) — Evidence:
  Assumed, specialist review flagged as advisable but not yet obtained.**
- **Minor-contractual-capacity risk — RESOLVED this cycle.** The
  rights-without-obligations doctrine holds; the Conradie v Rossouw
  citation is now fully verified. No open item remains in this risk
  category.
- **Terminology/perception risk — mitigation decided:** parent-facing-
  only debt terminology is adopted.
- **Late-penalty/relationship risk — both mitigation paths engaged:** the
  grace-period/pre-escalation reminder mechanism is committed
  (source-reduction) AND the specialist pilot-measurement package is
  adopted (residual tracking). Residual risk remains real.
- **Exam-bonus/intrinsic-motivation risk — now candidate-instrumented.**
  The behavior-primary redesign follows the evidence; the retained
  outcome-contingent bonus layer means the crowding-out risk is reduced,
  not eliminated. **This cycle: an Incubator-drafted candidate
  motivation-probe is added to the pilot instrumentation (Evidence:
  Assumed), pending child-development specialist review before it should
  be treated as validated.**
- **Fintech Advance content risk — mitigation adopted.**
- **Age-appropriateness/terminology-uniformity risk — framework adopted:**
  reconciliation with the product's six-way sub-bands is still to be
  done.
- **No-Mpoints fallback ripple risk:** conditional, not active.
- **Dispute-escalation risk:** unchanged.
- **Adoption/forecasting risk:** the funnel unit is resolved (per-family);
  the underlying install and conversion estimates remain the user's own
  lowest-confidence, unvalidated figures; the pilot's demand read will be
  directional only.
- **Competitive risk; monetization-execution risk; app-store policy
  risk; platform-concentration risk:** unchanged in substance.
- **Engineering-cost estimation risk:** subsumed into execution-capacity
  risk.
- **Legal-opinion-deferral risk:** RESOLVED at v17; retained for
  audit-trail continuity.

Status remains Complete: the risk landscape is comprehensively identified
and characterized, and every specialist-recommended mitigation within it
carries a recorded decision (adopted, adopted-as-hybrid with accepted
residual, or candidate-instrumented pending specialist review). A
Complete risk register does not mean the risks are eliminated: execution
capacity, two external regulatory questions, the accepted exam-bonus
residual, and the untested organic-only acquisition strategy are all
live, and are stated as such.

## Assumptions

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

Carried forward: parent-direct payment; SA launch jurisdiction; universal
consent gate; Android-first; Mbucks/Mpoints dual currency; 7-Mbuck
late-penalty cap with 3-Mbuck pilot cap; the fixed Mbucks-to-Rand peg;
the late-penalty mechanic as a parent-only administrative matter;
exam-bonus grade data self-reported/parent-entered; primarily a South
African B2C product at launch.

**Updated/new this cycle:**

- **The exam-bonus risk-acceptance assumption stands:** the secondary
  bonus's salience will not dominate the behavior-primary structure in
  the child's perception. Untested; now candidate-observable via this
  cycle's motivation-probe, pending specialist review of that probe's
  design.
- **New assumption: organic-only acquisition will be sufficient to reach
  a meaningful share of the 18,000-61,000 family-install funnel.**
  Untested, unbenchmarked against any South African comparable — a
  material, load-bearing assumption for the entire revenue model.
- **New assumption: the self-fund-further runway contingency is
  financially executable by the user at whatever scale is eventually
  required.** No specific amount or ceiling is stated; the commitment is
  directional, and its practical limits are unknown.
- **New assumption: the Incubator-drafted candidate data-breach
  commitment and motivation-probe are adequate as interim policy/design
  pending their respective specialist reviews.** Both are Evidence:
  Assumed by construction — neither has been reviewed by the specialist
  whose domain it falls within.
- The average children-per-family distribution within the up-to-4 cap
  remains unknown, now also affecting the child-to-family population
  conversion in Market & Competition (see that section's named residual
  gap).
- The user's policy covering professional opinions at zero marginal cost
  will continue to cover future engagements this case anticipates; its
  scope/limits are undocumented — Assumed.
- Mbucks non-transferability/non-redeemability and the SARB/NPS Act
  contingency remain as documented constraints rather than assumptions
  (see Constraints).

Status remains Partial: several new load-bearing assumptions are added
this cycle (organic-only sufficiency, self-fund-further executability,
candidate-content adequacy pending specialist review), none of which are
tested — the list remains a working inventory, not a closed set.

## Constraints

**Status:** Complete | **Confidence:** High | **Evidence:** Verified (with one Assumed-tier addition, named below)

- Solopreneur venture; AI-assisted development; external technical
  expertise engaged only on-demand; directional ~3-month build timeline;
  Android primary, iOS deferred.
- **Mbucks non-transferability/non-redeemability** — binding product-spec
  constraint on all future roadmap decisions (`LegalOpinion_v1.md` Q1).
- **R10,000 total development budget; 6-month runway before external
  funding is needed; professional opinions at zero marginal cost via the
  user's existing policy.** The runway, not the cash budget, is the
  binding constraint.
- **Zero paid acquisition — organic-only growth, DECIDED this cycle**
  (`Verdict_v4.md` required change 1). No marketing budget is allocated
  from the R10,000 total; this is a binding constraint on how the funnel
  can plausibly be filled, not merely a cost-saving choice.
- **Runway-slippage contingency — self-fund further, DECIDED this cycle,
  directional and uncosted** (`Verdict_v4.md` required change 2). If
  month 6 arrives without secured external funding, or any workstream
  slips, the user will personally extend the runway with additional
  personal funds rather than pause or close. **No specific additional
  amount or maximum extension period is specified — this is a
  directional commitment, not a costed one**, consistent with the case's
  practice of not inventing figures the user has not supplied. This is
  Verified-tier as to the decision itself; it is not Verified-tier as to
  magnitude, because no magnitude exists yet.
- **Minimal data-breach/incident-response commitment — Incubator-drafted
  candidate, this cycle** (`Verdict_v4.md` required change 5,
  `Clarifications_v20.md`). **Evidence: Assumed** — a founder-authored
  draft, not yet reviewed by the Data-Privacy Practitioner (Expert Roster
  Entry 5); that review is flagged as advisable before this is finalized,
  though not required to close this Investment Committee item. Candidate
  minimum content:
  - **What constitutes a breach:** unauthorized access to a minor's
    personal information or account data held by MiniMoney (e.g.
    credential compromise, unauthorized database access, misdirected
    disclosure).
  - **Who is notified:** affected parents (as the registered account
    holders and consent-givers); the South African Information Regulator,
    consistent with POPIA's Section 22 breach-notification obligation
    [Certain as to the statute existing; the specific notification
    process below is the Incubator's candidate operationalization of it,
    not a specialist-reviewed procedure].
  - **Timeframe:** notification "as soon as reasonably possible" after
    confirmed detection, consistent with POPIA's own standard (POPIA does
    not impose a fixed statutory clock comparable to GDPR's 72 hours) —
    no specific hour-count is invented here.
  - **Content of notification:** nature of the breach, the personal
    information reasonably believed to be affected, and measures taken or
    recommended to mitigate harm.
- **Launch-configuration constraints (decided fallbacks):** the product
  must be buildable in three configurations — full; without
  account-linking (SARB unresolved); without Mpoints (FPB unresolved).

Status remains Complete. The core constraint set (budget, runway, product
spec, acquisition, launch configurations) is Verified-tier as to what was
decided, including the newly-added acquisition and runway-contingency
items — both are genuine user decisions, even though the runway
contingency lacks a stated magnitude. **The data-breach commitment is a
distinct, Assumed-tier addition within this otherwise Verified-tier
section**, named as such rather than blended into the section's overall
tag.

## Roadmap

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Now (parallel with build, starting immediately):** the
curriculum-content workstream (instructional format, standards
alignment) runs alongside engineering. **Authorship remains EXPLICITLY
OPEN, not guessed** (`Verdict_v4.md` required change 4,
`Clarifications_v20.md`): the user has not yet decided between authoring
personally or engaging a curriculum designer via the zero-marginal-cost
advice policy, pending confirmation that policy's scope extends to
instructional-design expertise. The workstream proceeds regardless of who
authors it — only the "who" is open, named here as a genuinely pending
decision, distinct from every other item resolved this cycle.
(`CurriculumDraft_v1.md` exists as an earlier, unreviewed/unadopted
Incubator-drafted candidate, available only as a starting point.)

**Build phase:** implement core loop with decided designs —
parent-facing-only debt terminology; hybrid exam bonus; grace-period/
pre-escalation reminders; Fintech Advance without product gamification;
three-tier curriculum framing, including its reconciliation with the
six-way sub-bands. Legal build tasks: POPIA s14 retention period and
deletion trigger design; consent-flow documentation separation;
lightweight parent identity-verification step. **The candidate
data-breach/incident-response commitment (see Constraints) should be
reviewed by the Data-Privacy Practitioner (Expert Roster Entry 5) during
this phase, before real children's data is collected at pilot** —
flagged as advisable, not a hard gate.

**Build-spec stage:** the user personally runs both regulatory rechecks —
SARB/NPS Act and FPB (including the badge-residual check). Decided
fallbacks apply if unresolved by launch. **The Conradie v Rossouw
citation verification is now closed — removed from this stage's open
items.**

**Pilot (20-50 families):** double-duty per prior decision — mechanic
safety/child-development signal AND directional demand read — with the
adopted measurement package plus **this cycle's candidate
motivation-probe addition** built into the pilot design before
enrollment. **The candidate motivation-probe should be reviewed by the
child-development specialist (Expert Roster Entry 2) before pilot
instrumentation is finalized** — flagged as a recommended next step.

**Post-pilot (~month 6): external funding is needed** — the runway ends
here; a funding ask is not yet sized. **Decision rule, DECIDED this
cycle** (`Verdict_v4.md` required change 2): if month 6 arrives without
secured external funding, or any single workstream has slipped
materially, the user will self-fund further rather than pause or close —
directional, no specific amount or maximum extension stated.

**Growth (6-12 months):** conversion validation against the 1-3% range;
curriculum-engagement-as-retention-indicator validation; iOS port timing
evaluation; account-linking and/or Mpoints re-introduction as their
regulatory questions resolve; schools-partnership channel exploration
(still unplanned — no timeline, target, or resourcing).

Status remains Complete: every pre-pilot decision the roadmap listed as
pending is made or explicitly named as a pending decision (curriculum
authorship); remaining opens are owned external rechecks (now one fewer,
with the legal citation closed), build-spec parameters, and a
post-runway contingency that is directional but decided.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**What exists:**

- **Budget: R10,000 total** for development.
- **Professional advice: zero marginal cost** via the user's existing
  policy (scope/limits undocumented — Assumed).
- **Runway: 6 months** before external funding is needed.
- **Revenue model (per-family):** R59.99/month per family against a
  Year-1 range of 180-1,830 paying families — R10,798-R109,782/month
  run-rate at the range bounds; ramp-dependent actuals lower.
- **Acquisition spend: zero, decided this cycle.** No marketing budget
  is allocated; growth is organic-only.
- **Runway-slippage contingency: self-fund further, decided this cycle —
  directional, not costed.** No specific additional amount or maximum
  extension period is specified.

**The reconciliation, stated as the Investment Committee would want it:**
R10,000 (~$550) against the previously-cited $25,000-$120,000+ agency
range is a 45×-220× gap, coherent only as a founder-labor-plus-AI-
assisted build. **The 6-month runway is the binding constraint**, now
with a stated (if uncosted) fallback rather than an unaddressed cliff:
build, parallel curriculum authoring, instrumented pilot, and two
user-owned regulatory rechecks must all complete inside it, after which
funding is needed with — at best — directional pilot evidence to raise
on, or the user extends the runway personally by an unspecified amount.

**This cycle's decisions close one previously-named open item (CAC/
marketing budget — now decided as zero) and partially address a second
(runway contingency — now decided, though not sized).** Still absent,
named: curriculum content production cost; the size and form of the
post-runway funding ask (the self-fund-further decision states a
direction, not a size); full financial projections (P&L, break-even).
Status remains Partial: the section now has a real budget, runway,
acquisition decision, and runway contingency, but the funding-ask sizing,
content-production cost, and break-even analysis that would complete it
do not yet exist. Per Playbook Entry 1, stated explicitly: this cycle's
resolutions are decisions, not new financial data, and they close one
full named gap and narrow (without closing) a second — Status does not
move as a result, consistent with the section's own remaining opens
being independent of what this cycle resolved.

## Validation Strategy

**Status:** Partial | **Confidence:** High | **Evidence:** Supported

**Closed streams:** legal validation (retained opinion, Verified-tier,
**now fully closed including the citation dependency**); child-
development/age-appropriateness validation (retained review,
Verified-tier); all six resulting design recommendations carry decisions.

**Pilot — scope decided: double duty**, with the reviewer's underpowering
caution attached: demand findings will be directional and qualitative,
not statistically validated. **This cycle: the adopted measurement
package is extended with a candidate motivation-probe** (see Success
Criteria), itself pending specialist review before it should be treated
as validated instrumentation — a validation-of-the-validation-instrument
gap, named explicitly rather than assumed away.

**Still open:** pricing/conversion validation (the pilot may inform
willingness-to-pay directionally but is not a conversion test);
curriculum validation (no content yet exists to validate, and curriculum
authorship itself remains an open decision — see Curriculum Design);
account-linking UX/consent-flow validation; the no-Mpoints fallback
configuration's engagement loop has no validation plan; **whether
organic-only acquisition can reach the funnel's stated range has no
validation plan of any kind anywhere in the case.**

Status remains Partial: the pilot is fully scoped and instrumented at the
decision level, including a candidate motivation-probe pending specialist
review, but market demand, pricing/conversion, and now acquisition
feasibility have no statistically meaningful validation scheduled
anywhere in the plan.

## Supporting Evidence

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Verified-tier:** `LegalOpinion_v1.md` and `ChildDevelopmentReview_v1.md`
(retained professionals); the user's direct clarification history
through **`Clarifications_v20.md`** (Verified-tier as to what was
decided: acquisition strategy, runway contingency direction, curriculum
authorship left explicitly open, and — via `Clarifications_v19.md`,
incorporated this cycle — the Conradie v Rossouw citation closure).

**Supported-tier:** three Research House engagements
(`ResearchFindings_v1-3.md`); the user's directly-cited South African
statutory/statistical sources; **`BusinessCase_v16.md`'s restored Market &
Competition content**, now directly traced rather than reconstructed
from a thinner intermediate version.

**Assumed-tier, named explicitly this cycle:** the candidate
motivation-probe addition (Success Criteria, Operations); the candidate
data-breach/incident-response commitment (Constraints) — both
Incubator-drafted per direct Chief of Staff instruction, neither yet
reviewed by the specialist whose domain it falls within.

**Bounded first-party data:** the n=10 interview round — non-
representative, governed by the standing instruction; the same rule
extends to the pilot's directional demand findings.

**Evidence-chain limitations, updated this cycle:** `BusinessCase_v16.md`'s
Market & Competition narrative — previously not among an authorized-input
set for two consecutive cycles — is now directly incorporated,
**resolving** the evidence-chain limitation named at v18. **The Conradie v
Rossouw citation is fully verified, resolving** the second limitation
named at v18. **New limitation, named:** the candidate motivation-probe
and data-breach commitment are Assumed-tier pending specialist review,
not yet elevated even to Supported.

Status remains Complete: the evidentiary base spans Verified-tier user
decisions and retained-professional opinions through Supported-tier desk
research to bounded first-party data and named Assumed-tier candidate
content, with each tier's limits stated.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle:** acquisition/CAC strategy (organic-only, zero
paid); runway-slippage contingency direction (self-fund further,
uncosted); the Conradie v Rossouw pinpoint citation and substantive
proposition (both fully verified).

**Newly named this cycle:**

- **Curriculum authorship — EXPLICITLY OPEN, a genuinely pending user
  decision**, distinct from every other item this cycle, which is
  resolved: personal authorship vs. engaging a designer via the
  zero-marginal-cost advice policy, pending confirmation that policy's
  scope extends to instructional-design expertise.
- **Child-to-family population-conversion gap in Market & Competition:**
  the population-base derivation is computed at the child level; no
  separate family-level re-derivation exists that accounts for the
  up-to-4-children-per-family distribution (itself unknown).
- **Specialist review of the candidate motivation-probe** (child-
  development specialist, Expert Roster Entry 2) — recommended next
  step, not yet engaged.
- **Specialist review of the candidate data-breach/incident-response
  commitment** (Data-Privacy Practitioner, Expert Roster Entry 5) —
  flagged as advisable, not yet engaged.
- **Whether organic-only acquisition can plausibly reach the
  18,000-61,000 family-install funnel** — untested, unbenchmarked.
- **Sizing of the self-fund-further contingency** — no amount or ceiling
  specified.

**Open — design/build tasks, unchanged:** POPIA s14 retention period and
deletion trigger; consent-flow documentation separation; lightweight
parent identity-verification; grace-period length and reminder cadence;
behavior-input logging/verification and grade-input mechanisms for the
hybrid bonus; the no-Mpoints fallback's feature-table variant and 6-9-
tier immediate-feedback replacement; dispute-escalation mechanism beyond
the 48-hour window; the "request for payment" prompt feature's coherence
under the child-invisible late-penalty model; account-linking opt-in UX
flow; task verification mechanics.

**Open — analytical/planning gaps, unchanged:** three-tier curriculum
framework reconciliation with the six-way sub-bands; curriculum
instructional format, standards alignment, and content (workstream
committed and starting, content nonexistent, authorship now explicitly
open); curriculum-engagement (30%), operational-health (65%), and
retention benchmarks (placeholders); curriculum content production cost;
post-runway funding ask size and form; the schools-partnership channel's
timeline/target/resourcing; MoneyAfrica Kids' unpublished premium price;
South Africa-specific vendor pricing for Stitch's or Mono's product; the
user's advice-policy scope/limits (including whether it covers
curriculum expertise — the same open question underlying curriculum
authorship).

Status remains Complete: this register's scope is comprehensive
identification and tracking, and every item carries its disposition (in
flight, build task, conditional, named gap, or explicitly pending
decision) — none is an undecided recommendation silently awaiting a
decision without being named as such.

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**"Complete" definition, unchanged from v18, applied consistently:** a
section is Complete when every material question within its scope has a
made decision — resolved, adopted, or a deliberate, documented
residual-risk acceptance — and anything still open is a tracked
implementation detail, build-spec parameter, or externally-gated recheck
carrying a named owner and (where launch-relevant) a decided fallback. A
section carrying an undecided specialist recommendation or an unmade
material decision is Partial. For register-type sections (Risks,
Outstanding Questions), Complete means comprehensive identification with
a recorded disposition per item.

**This cycle's specific test of that definition:** does an
Incubator-drafted candidate (the motivation-probe; the data-breach
commitment), explicitly not yet specialist-reviewed, count as a "made
decision" within its section's scope? **No — treated consistently with
the definition's own text:** "documentation of an open decision is not
resolution of it," and a candidate awaiting a named, recommended review
is a variant of exactly that. This is why Success Criteria and
Constraints' data-breach item are handled differently: Constraints as a
whole remains Complete because its *other* material questions (budget,
runway, acquisition, runway contingency) are genuinely decided, with the
breach commitment flagged as a distinct Assumed-tier addition rather than
counted as resolving a material question in its own right; Success
Criteria remains Partial in part because its own pre-existing gaps
(unbenchmarked curriculum/operational/retention criteria) are untouched,
independent of the motivation-probe's own status.

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
| Business Model | Complete | 1x | 5 |
| Revenue & Costs | Partial | 1x | 2 |
| Operations | Complete | 1x | 5 |
| Technology | Partial | 1x | 2 |
| Legal & Compliance ★ | Complete | 2x | 10 |
| Risks | Complete | 1x | 5 |
| Assumptions | Partial | 1x | 2 |
| Constraints | Complete | 1x | 5 |
| Roadmap | Complete | 1x | 5 |
| Financial Considerations | Partial | 1x | 2 |
| Validation Strategy | Partial | 1x | 2 |
| Supporting Evidence | Complete | 1x | 5 |
| Outstanding Questions | Complete | 1x | 5 |
| Curriculum Design (extension) | Partial | 1x | 2 |
| Child Data & Consent (extension) ★ | Complete | 2x | 10 |

Points earned: **91**.

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130.**

**Readiness Score = 91 / 130 = 70.0%.** Clears the completion gate's
≥70% threshold, with no margin.

No section is Critical + Incomplete: both Legal & Compliance and Child
Data & Consent are Complete.

**Why the score is unchanged from v18 (stated explicitly per Playbook
Entry 1):** this cycle's work is dominated by (a) a data-integrity
restoration (Market & Competition) that, by its own nature, cannot move a
Status-based score — it restores evidentiary detail, not new decisions —
and (b) decisions and candidate drafts that either resolve items inside
sections already scored Complete (Legal & Compliance's citation closure;
Constraints' acquisition and runway-contingency additions), or partially
close named opens inside sections that retain other, independent,
untouched gaps (Revenue & Costs and Financial Considerations both had
their CAC item resolved but retain unpriced curriculum content and an
unsized funding ask; Success Criteria gained a candidate instrument but
retains unbenchmarked criteria elsewhere). No section's Status moved in
either direction. Per Playbook Entry 3: no section's Confidence declined
this cycle, and none rose either — Market & Competition's restoration
explicitly does not raise Confidence, stated above and per this cycle's
specific instruction.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → 52% (v14) → 52% (v15) → 52% (v16) → 70% (v17) → 70% (v18) →
**70% (v20) — flat a second consecutive cycle.** (There is no
`BusinessCase_v19.md`; `Clarifications_v19.md`'s legal-citation finding
was resolved off-cycle and is incorporated into a Business Case for the
first time in this version.)

### Critical Gaps

1. **Execution capacity (Financial Considerations, Constraints, Risks) —
   still the binding constraint, now with a stated but uncosted
   contingency.** R10,000 total development budget plus a 6-month runway
   must contain the build, curriculum authoring, an instrumented pilot,
   and two regulatory rechecks — executed substantially by one person.
   **This cycle: a self-fund-further contingency exists if the runway
   slips or month 6 arrives unfunded — directional, no specified amount.**
2. **SARB/National Payment System Act open-banking question — owned and
   fallback-protected, still externally unsettled.** Owner: the user, at
   build-spec stage; decided fallback: launch without account-linking.
3. **FPB classification question over Mpoints — owned and
   fallback-protected, still externally unsettled, with traced ripple
   effects.** Owner: the user, at build-spec stage; decided fallback:
   launch without Mpoints.
4. **Market demand remains directionally evidenced only.** The n=10
   standing instruction holds; the pilot's demand read will be
   directional/qualitative, not validated. **This cycle adds a related,
   untested item: whether organic-only acquisition (now decided) can
   plausibly reach the 18,000-61,000 family-install funnel at all.**
5. **Success-criteria benchmarks remain placeholders.** Curriculum
   engagement (30%) and operational health (65%) carry no external
   benchmark; retention has no proposed figure at all.
6. **Curriculum content does not yet exist, and authorship is now
   explicitly named as an open decision (not merely unspecified).** The
   three-tier framework is adopted and the parallel workstream is
   committed starting now, but who authors the content — the user, or a
   designer engaged via the zero-marginal-cost policy, pending
   confirmation that policy covers instructional-design expertise — is
   genuinely undecided.
7. **Legal/build tasks pending, one item now with a drafted candidate.**
   POPIA s14 retention period and deletion trigger; consent-flow
   documentation separation; lightweight parent identity-verification.
   **A minimal data-breach/incident-response commitment now exists as an
   Incubator-drafted candidate (Constraints), Evidence: Assumed —
   Data-Privacy Practitioner review flagged as advisable, not yet
   obtained.**
8. **Exam-bonus residual risk — accepted, now candidate-instrumented, not
   yet specialist-reviewed.** The hybrid's retained outcome-contingent
   bonus layer carries a reduced-but-real intrinsic-motivation risk. **An
   Incubator-drafted candidate motivation-probe now exists (Success
   Criteria), Evidence: Assumed — child-development specialist review
   flagged as a recommended next step, not yet obtained.**
9. **RESOLVED this cycle, retained for audit-trail continuity:**
   acquisition/CAC strategy (organic-only, zero paid); runway-slippage
   contingency direction (self-fund further, uncosted); **Conradie v
   Rossouw pinpoint citation and substantive proposition — fully
   verified, closing what was previously Critical Gap #8.**
10. **Resolved in prior cycles, retained for audit-trail continuity:**
    all six original specialist design decisions; the subscriber-count
    discrepancy and family-vs-child ambiguity (per-family; 180-1,830
    survives); recheck ownership/timing/fallbacks; pilot scope;
    cost/runway.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** High | **Evidence:** Verified (authorship item: Unknown)

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs.*

Carried forward: the age floor of 6 is intentional; the curriculum is a
short course completable daily or weekly, not a full year; two example
mechanics (currency differentiation; "word sums" for change/remainder
calculation); "Fintech Advance" as the distinct 15-18-only element
(gamification-avoidance decided, risk-literacy framing adopted).

**Three-tier age framework — adopted:** early childhood (roughly 6-9,
softened task/reward framing); pre-teen (roughly 10-14, basic
transactional literacy); teens (roughly 15-18, pre-employment literacy).
Workstream timing decided: curriculum content authoring runs in parallel
with the engineering build, starting now.

**Authorship — EXPLICITLY OPEN this cycle, not guessed**
(`Verdict_v4.md` required change 4, `Clarifications_v20.md`). The user
has not yet decided between authoring the curriculum personally or
engaging a curriculum designer via the zero-marginal-cost advice policy —
this is genuinely pending confirmation of whether that policy's scope
extends to curriculum/instructional-design expertise, not just legal
advice. **This is a named, pending decision, distinct from every other
item resolved this cycle.** The curriculum workstream remains committed
to start in parallel with the build regardless of who authors it — only
the "who" is open. `CurriculumDraft_v1.md` exists as an earlier,
unreviewed/unadopted Incubator-drafted candidate, available only as a
starting point, not a resolution of the authorship question.

**Still open:** instructional format, standards alignment, and content
itself (the workstream exists; its outputs, and now even its author, do
not); reconciliation of the three-tier framework with the product's
existing six-way stakeholder sub-bands — still not done; the conditional
6-9-tier immediate-feedback replacement under the no-Mpoints fallback.
The 30% curriculum-engagement success benchmark remains unbenchmarked.

Status remains Partial: the framework and workstream timing are decided,
but the section's core deliverable — actual instructional content, and
now explicitly who will produce it — does not yet exist.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Directly and substantially addressed by `LegalOpinion_v1.md` Q2 and Q3.
The universal parent-consent gate is confirmed legally sufficient as
designed under POPIA s34/s35(1)(a). Two hardening recommendations remain
named build tasks: consent-flow documentation separation; a lightweight
parent identity-verification step (non-linking route required if the
SARB fallback triggers).

POPIA Section 14 retention is confirmed to require an affirmatively
designed, specific retention period and deletion trigger — a named,
pending build task.

**New this cycle: a minimal data-breach/incident-response commitment
(see Constraints for full text) directly extends this section's scope.**
It is an Incubator-drafted candidate (Evidence: Assumed), specifying what
constitutes a breach, who is notified (parents; the Information
Regulator, per POPIA s22), and a notification timing standard consistent
with POPIA's "as soon as reasonably possible" language rather than an
invented fixed clock. **Specialist (Data-Privacy Practitioner) review is
flagged as advisable before real children's data is collected at pilot,
though not required to close the Investment Committee item that
prompted this draft.**

Platform-policy items, unchanged: Google Play's Families Policy
loyalty-point disclosure requirement applies to the primary configuration
and is mooted under the no-Mpoints fallback; Apple's Kids Category
IAP-currency question is deferred with iOS and likewise mooted under that
fallback.

Status remains Complete: the section's central questions — consent-model
sufficiency and retention approach — are directly answered by retained
counsel; the new candidate breach commitment is an additive strengthening
flagged for specialist review, not an unresolved central question of the
section's own original scope.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**
- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Complete.
- Readiness Score ≥ 70%: **Yes — PASSES, with no margin.** Score is
  70.0% (91/130), unchanged from v18 — explained explicitly in the
  Readiness Score section.
- **Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption — addressing `Verdict_v4.md`'s Gate Integrity
  observation with in-document substance, not a bare pointer this time:**
  see `ExpertRoster.md`, regenerated this cycle. Representative excerpt
  (Entry 5, Data-Privacy Practitioner): *"...assumes the founder's
  zero-marginal-cost professional-advice policy will cover a
  privacy-specific review even though the policy's own scope was never
  documented as extending beyond the legal opinion it has funded so
  far..."* — a specific case assumption (the advice-policy's undocumented
  scope, carried since v18's Assumptions section) named directly, not a
  generic domain concern.
- **Devil's Advocate objections ≥3, each citing a specific section —
  same treatment:** see `reviews/DevilsAdvocate.md`, regenerated this
  cycle. Representative excerpt (Objection 1): *"The self-fund-further
  contingency (Constraints, Financial Considerations, Critical Gaps §1)
  is a decision in name only until it carries a number — an unlimited
  personal commitment is not a real constraint, it is the absence of
  one..."*
- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.
- No section consists solely of an "Unchanged from vN, not reproduced"
  pointer: **Yes.** Market & Competition — the section most exposed to
  this failure mode across three prior cycles — is restored to
  self-contained, directly-traced text this cycle, verified against
  `BusinessCase_v16.md` itself rather than a later reconstruction. Every
  section contains its own full, substantive, self-contained text.

**This Business Case passes its own completion gate.** All six of the
Investment Committee's required changes from `Verdict_v4.md` are
resolved — three by direct user decision (acquisition, runway
contingency, curriculum authorship named as explicitly open), two by
Incubator-drafted candidate content per direct instruction (motivation-
probe, data-breach commitment), and one (legal citation) fully closed.
The carried-over Market & Competition data-integrity fix restores the
section to its actual v16 content, explicitly without inflating its
Confidence or Evidence tags. Genuine open items remain — detailed in
Critical Gaps — led by execution capacity (now with an uncosted
contingency), two externally-unsettled regulatory questions, curriculum
authorship (now an explicitly named pending decision), and two
Incubator-drafted candidates awaiting the specialist review each is
flagged as needing.
