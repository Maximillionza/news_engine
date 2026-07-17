# Business Case: MiniMoney — v16

> Prepared by: Incubator. **This is a second consolidation cycle, not a
> clarification-driven revision.** The first consolidation
> (`BusinessCase_v15.md`) traced ten bare-pointer sections back only to
> `BusinessCase_v9.md` as a baseline, but a Chief of Staff audit found that
> several sections had already lost real content *before* v9, at the
> sub-section level — not merely as whole-section pointers. This cycle's
> authorized inputs are the full version history: `00_CaseStudy.md`,
> `BusinessCase_v1.md` through `BusinessCase_v15.md`, `Clarifications_v2.md`
> through `Clarifications_v14.md` (all available versions),
> `ResearchFindings_v1.md` through `ResearchFindings_v3.md`, and
> `Verdict.md`. Every section below was checked against the earliest
> version where it was last genuinely complete, not assumed to be v9 or
> v15, and restored in full wherever content was silently dropped rather
> than genuinely superseded. Where a later decision actually changed a
> fact (the late-penalty cap, the consent model, the monetization
> decision, the subscription price, the account-linking design), the
> latest decision is used, never the superseded content.

> **What this cycle specifically found and fixed, beyond v15's own
> corrections:**
>
> 1. **Value Proposition** was missing the full Free/Subscription feature
>    table and the full description of "Fintech Advance." `BusinessCase_v9.md`
>    collapsed this to "unchanged from v8" without reproducing it, and no
>    version since restored it — including v15, which reconstructed this
>    section from v9's own text and therefore inherited the gap. The table
>    and description are fully present in `BusinessCase_v8.md` (the table)
>    and `BusinessCase_v6.md` (the full Fintech Advance narrative), and are
>    restored below in full, reconciled with every later decision that
>    actually touched them (the subscription-only monetization decision at
>    v8, which is why the table now reads "Free/Subscription" rather than
>    v6's original "Freemium/Paywall" headers).
> 2. **Curriculum Design (domain extension)** was missing the age-6
>    rationale, the curriculum shape ("short daily/weekly-completable
>    course, not a full year"), and the two named example mechanics
>    (currency differentiation; "word sums" for change/remainder
>    calculation). This content was already reduced to a bare pointer by
>    `BusinessCase_v9.md`; the fullest version is `BusinessCase_v6.md`.
>    Restored in full below.
> 3. **Market & Competition** was already reduced to "see v7 for full
>    detail" by `BusinessCase_v8.md` — meaning v9 was never a complete
>    baseline for this section, and v15's reconstruction (which explicitly
>    disclosed it could not access v8) inherited a real gap, not an
>    unavoidable one. The richest version of this content — Stats SA
>    population figures, the 2024 Stellenbosch device-ownership study,
>    Statcounter OS-share data, the SARB Payments Study, the
>    reachable-market funnel derivation, and **all three** named South
>    African competitors — is in `BusinessCase_v6.md`. Restored in full
>    below, reconciled with the now-resolved subscription-only conversion
>    rate and combined with the international comparables research
>    (`ResearchFindings_v2.md`) that v15 had already correctly added.
> 4. **Spot-check findings beyond the three flagged sections:** Stakeholders
>    and Target Users/Customers, in v15, incorrectly flagged the minors'
>    age sub-band boundaries as "not present in any input available to this
>    reconstruction cycle" — they are, in fact, stated plainly in
>    `BusinessCase_v6.md`, `v7.md`, and `v8.md` (sub-bands 6, 7, 8, 9-10,
>    11-14, 15-18) and are restored below. Market & Competition and
>    Stakeholders, in v15, also incorrectly flagged the third named
>    competitor as "Unknown" — it is African Bank's MyWORLD Power Pocket,
>    present in the same three versions, and is restored below. Objectives,
>    in v15, incorrectly stated that Pre-launch and Growth-phase objectives
>    beyond the 90-day/annual figures were "not independently detailed in
>    any input available to this reconstruction cycle" — they are detailed
>    in `BusinessCase_v6.md` through `v9.md` and are restored below. Risks,
>    carried forward unchanged since v13 (itself carried forward from v12,
>    which this cycle cannot access, but v9's own full text is available
>    and authoritative), had silently dropped three named risk categories
>    present continuously from v6 through v9 — dispute-escalation risk,
>    advertising/child-data risk, and Fintech Advance content risk — which
>    are restored below.
>
> **Where content was genuinely superseded, the later decision is used,
> not the older content.** The late-penalty cap (5→6→7 Mbucks/week, pilot
> cap 3) reflects the v6 correction, unchanged since. The consent model
> reflects the v14 removal of the v12 pre-link carve-out (universal,
> parent-first, no exceptions). Monetization reflects the v8
> subscription-only decision (not v6's original Freemium/ads framing).
> Pricing reflects the v10 R59.99/month, up to 4 children figure. The
> late-penalty visibility reflects the v10 redesign (parent-only,
> child-invisible). Account-linking reflects the v14 "optional, not
> excluded" decision. No restored content is allowed to contradict any of
> these five superseding decisions; where v6-v9 language is restored
> verbatim below, it has been checked against each of these five
> decisions first.

## What Changed in v16 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Four sections received substantive content restoration beyond v15's own
consolidation: Value Proposition (Free/Subscription table + full Fintech
Advance description), Curriculum Design domain extension (age-6 rationale,
curriculum shape, two example mechanics), Market & Competition (full
population/device/OS/SARB/competitor data and funnel derivation), and
Risks (three dropped risk categories restored). Two further sections —
Stakeholders and Target Users/Customers — had a specific factual error
corrected (age sub-bands and the third competitor's identity are not
Unknown; they are documented in the version history and are restored).
Objectives had its Pre-launch and Growth-phase content restored.

**Net effect on Status (Readiness Score): none.** No section's Status
changes as a result of this cycle. Every restoration closes an
*evidentiary* gap (content that existed but was not reproduced), not a
*substantive* one (a genuine open question the user has not yet answered)
— the sections affected were already Complete or Partial for reasons that
restoring this content does not resolve (Value Proposition was already
Complete; Curriculum Design, Market & Competition, Stakeholders, Target
Users/Customers, Risks, and Objectives' own residual open items are
unaffected). The Readiness Score is recomputed in full below and confirmed
**unchanged at 52% (67/130)**.

**Net effect on Confidence: two sections rise, stated explicitly per
Playbook Entry 3 (track Confidence trajectory separately from Status) and
Playbook Entry 4 (a rising Confidence tag means a clearer picture, not
automatically better news).**

- **Value Proposition: Confidence Medium → High.** v15 held this section
  at Medium specifically because of "this residual gap" — the missing
  free-vs-subscription feature-boundary detail. That gap is now closed:
  the table exists, and it is Verified-tier evidence (a direct user
  hand-edit, scoped by `Clarifications_v6.md`). With both the price
  (Verified, since v10) and the feature split (Verified, restored this
  cycle) now present, nothing remains to hold Confidence below High.
- **Curriculum Design: Confidence Low → Medium.** v15 explicitly
  downgraded this to Low, reasoning that the section's "actual
  evidentiary base consists of one sentence from the original case study
  and four named-but-undetailed open questions." That reasoning was
  correct *given v15's own available inputs*, but this cycle's fuller
  trace shows the evidentiary base was never that thin — it just stopped
  being reproduced after v9. This is a correction to v15's assessment,
  not new information: per Playbook Entry 4, this is stated as
  "the picture is clearer, and the underlying evidentiary base was always
  better than v15's isolated vantage could show," not as a new, more
  favorable development. Status remains Partial — the four
  named open items (age-band splits, instructional format, standards
  alignment, content authorship) are still genuinely unresolved.

**A candidate playbook lesson arising directly from this cycle** is
proposed in this Incubator's final message to the Chief of Staff, not
written here.

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

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
up to 4 children per family account. Monetization is subscription-only at
launch, with advertising deferred to a possible post-launch V2. Real-money
in-app purchases remain parent-only. The late-payment penalty mechanic is
incurred entirely by the parent (5→6→7 Mbucks/week, pilot cap 3); the
child has zero visibility into it. A distinct, 15-18-only curriculum
element, "Fintech Advance," teaches the concepts of trending/
entrepreneurial ventures (forex trading, dropshipping) with no in-app
trading execution, gated by a separate explicit parent opt-in in addition
to the general subscription unlock — described by the user as a
"non-negotiable requirement" for that age band's curriculum.

A minor cannot register an account, nor access any part of the app,
without a parent acting as registration custodian from the outset. A
brief pre-link independent-registration carve-out (allowing a minor to
independently register and access a practice-only budgeting feature
before any parent link existed) was introduced at v12 and removed again
at v14 — the case reverts to, and reaffirms, the universal
parental-consent gate established at v5. There is no longer any point at
which a minor's account exists, or their data is processed, ahead of
parental consent.

Account-linking is now an optional, parent-controlled feature, not an
exclusion. A parent may optionally link a read-only bank view (via a
Stitch/Mono-style integration) to help verify a child's payment; honor-
system self-report remains the default path for parents who decline to
link. The underlying regulatory question — whether the NCR or any other
South African regulator actually reaches a read-only, non-custodial
account-verification service — remains unresolved by desk research and
gates this feature's ship date behind the still-uncommissioned specialist
legal opinion.

Neither of these two design changes resolves the underlying, still-open
legal questions (contractual capacity; domestic-agreement presumption;
ARB precedent absence; whether the NCR regulates read-only linking) —
both Critical Legal sections remain **Partial**, and Confidence holds
flat at **Medium**, bounded by these unrelated, untouched items. The
Readiness Score is **52% (67/130)**, confirmed unchanged by this cycle's
full recomputation. This cycle's own work — restoring content silently
dropped from Value Proposition, Curriculum Design, Market & Competition,
Risks, Objectives, Stakeholders, and Target Users/Customers across the
full version history — improves the document's completeness and
traceability materially without moving the Status-based score, consistent
with Playbook Entry 1.

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
expressed interest specifically in the education aspect. This is genuine,
first-party, MiniMoney-specific evidence, categorically different from
comparable-market inference, but it is not statistically significant —
sampling method, recruitment channel, family-selection criteria, and
exact question wording are all unknown. Per a standing instruction
adopted at v9 and reaffirmed at v10 (`Clarifications_v10.md`: "accept it
stays bounded as non-representative"), this data point must not be used,
in this or any future version, as if it were a representative or
validated demand signal — in funnel modeling, in Financial
Considerations, in Objectives, or anywhere else — until either (a) its
methodology is documented retroactively (recruitment channel, sampling
frame, exact question wording), or (b) it is superseded by the
already-planned 20-50 family pilot or a structured survey. This
instruction exists precisely because a directional, encouraging n=10
result can otherwise quietly accumulate more evidentiary weight across
successive versions than it warrants.

No clarification or research finding after v9 has revisited the core
Problem framing itself. Status remains Partial for the same reason it has
since v8: this is a real, encouraging, directional signal, not an
established finding that parents broadly perceive this as a problem worth
paying to solve.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

If financial literacy for minors is an underserved niche, MiniMoney's
differentiator is the payroll-simulation mechanic rather than a simple
debit-card-for-kids model, framed as an edtech app with a
payroll-simulation UX. No direct South African incumbent does what
MiniMoney does. `ResearchFindings_v1.md` Item 5 (carried from v7) adds a
directional data point: MoneyAfrica Kids shows modest download volumes
(10,000+ Google Play, 3,000+ Apple, pan-African not SA-specific), while
MoneyTime SA claims a larger, self-published B2B2C-mediated reach
(130,000 students via schools) — together suggesting real but unproven
consumer appetite, with the strongest demonstrated reach coming via a
schools-distribution model. Distribution strategy treats a
schools-partnership channel as an intended, parallel channel alongside
direct-to-parent acquisition, not a rejected alternative (clarified at
v8, correcting an earlier v7 mischaracterization) — the
schools-partnership timeline, target school count, and resourcing plan
remain open items (see Outstanding Questions).

The subscription price now confirmed (R59.99/month, up to 4 children per
family, per `Clarifications_v10.md`) sharpens the competitive read against
MoneyTime SA's R995/year (25% sibling discount): MiniMoney's price,
expressed monthly, sits below MoneyTime SA's annualized rate even before
the sibling discount is applied, which is relevant opportunity context
but does not on its own establish market size or demand — that remains
governed by the same n=10, non-representative bound described in Problem.
Status remains Partial: the differentiation thesis is coherent and
partly evidenced, but no structured market-sizing or validated demand
study has been conducted.

## Objectives

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

The functional objective is: budget → tasks → Mbuck/Mpoint earning →
exam bonus → invoice/payslip → payment confirmation with escalating
late-penalty → age-gated education. As of `Clarifications_v10.md` and
`Clarifications_v14.md`, the late-penalty step in this flow is incurred
entirely by the parent and is invisible to the child (see Success
Criteria, Legal & Compliance); this does not change the objective
sequence itself, only who bears and sees the late-penalty consequence
within it.

**Pre-launch and Growth-phase objectives, restored this cycle — present
continuously from `BusinessCase_v6.md` through `v9.md`, dropped from v10
onward without being superseded by any later decision:**

- **Pre-launch:** validate the core budget→task→Mbuck/Mpoint→payslip→
  payment loop, including the dispute and late-penalty mechanics, with a
  small pilot cohort of South African families (candidate target: 20-50
  families) before wider release, on the confirmed Android platform. The
  n=10 interview round (see Problem) is a first, informal step in this
  direction but is not itself this pilot.
- **Growth (6-12 months):** validate the subscription-conversion
  assumption against the **1-3% subscription-only** reference range (the
  2-4% ads-hybrid range cited in earlier versions is no longer the
  applicable benchmark, following the subscription-only monetization
  decision confirmed at v8); validate curriculum engagement as a leading
  indicator of retention; evaluate iOS port timing based on Android
  traction.

**The 90-day (15,000 installs) vs. annual funnel (18,000-61,000
installs) target tension — resolved via `Clarifications_v10.md`, not
merely quantified.** At v9, the Incubator established the arithmetic
precisely without resolving it: a strictly linear pace against the
annual range's low end would imply ≈4,438 installs in 90 days, not
15,000 — the stated 90-day target was roughly 3.4x a linear-pace reading
of the annual low end, and almost exactly consistent with a linear
reading of the high end (61,000). This left two paths open: state an
explicit front-loaded launch-marketing assumption, or revise the 90-day
target downward.

`Clarifications_v10.md` resolves this directly. The user's own framing:
"We are targeting onboarding at least 100 a day for the first 90 days,"
clarified on follow-up as **"The 100 per day is the floor target with
the intention to increase the adoption rate above this."** This confirms
the front-loaded-growth path, not a target revision: 100/day × 90 days =
9,000 as an explicit *minimum* floor, while the retained 15,000-in-90-days
figure requires an average of ≈167/day across the window — well above
the 100/day floor, consistent with a ramping adoption curve rather than a
flat rate, and internally consistent with the annual range's high end as
already shown at v9. The tension is resolved in the sense the Investment
Committee required ("resolved, not described"): the business now has an
explicit, user-confirmed floor-plus-ramp model rather than an
unreconciled flat-rate mismatch.

Status is raised to **Complete**: the specific tension the Investment
Committee required resolved is now resolved by a direct, Verified-tier
user clarification, not merely bounded analytically, and the Pre-launch/
Growth-phase content restored this cycle closes the gap flagged (in
error) by v15 as unavailable in any input. Confidence and Evidence are
set to **High/Verified** for this reason — this is the highest
evidentiary tier this case uses, reserved for facts the user has
personally confirmed.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Core criteria, carried from v8/v9: pilot success (majority of families
complete ≥4 consecutive weekly cycles, with the 48-hour dispute window and
late-penalty mechanic exercised and tracked, and running arrears visible
as a line item to the parent — see Legal & Compliance and Operations for
the now-parent-only visibility redesign); curriculum engagement (30%, no
external benchmark); operational health (65% task-completion without
dispute, no external benchmark); freemium/subscription conversion (2%,
correctly benchmarked against the 1-3% subscription-only range);
retention (no figure proposed).

**Family-relationship-strain criterion, added at v9 (Investment Committee
requirement #5), reframed at v10 following the late-penalty redesign.**
The v9 requirement was to track relationship-strain indicators segmented
by child age band, since the escalating late-penalty mechanic (5→6→7
Mbucks/week, pilot cap 3) plausibly lands very differently on a 6-year-old
than a 17-year-old. `Clarifications_v10.md` then redesigned the mechanic
itself: the parent alone incurs the penalty, and the child has **zero
visibility** into whether a penalty was charged or how much is owed. This
substantially narrows, but does not eliminate, the direct child-facing
version of this risk — a child who cannot see a penalty cannot be
directly distressed by it in the way the original criterion assumed. The
user's own framing when supplying this redesign explicitly anticipated
this: the Incubator was asked to assess "whether this substantially
narrows (though perhaps does not fully eliminate — a parent's own stress
or behavior around an accumulating obligation could still indirectly
affect the child) the child-development risk."

Accordingly, the relationship-strain criterion is reframed here, not
retired: candidate metrics should now target *indirect* effects — a
parent's own financial stress or behavioral change around an
accumulating, child-invisible penalty obligation, and whether that stress
measurably surfaces in the household regardless of the child's lack of
direct visibility — rather than child-reported friction over a penalty
amount the child can no longer see. Candidate metrics, none yet adopted
or measured: parent-reported friction/conflict incidents plausibly
traceable to the penalty obligation even though not disclosed to the
child; dispute frequency (now necessarily parent-only, since the child
cannot dispute a penalty they cannot see) segmented by child age band;
pause/opt-out rate by age band; a simple pre/post parent-reported
household-stress indicator specific to the payslip/penalty mechanic. No
such metric currently exists in any input available to this
reconstruction cycle — this is a reframed, not a newly invented,
requirement, and it stands until the pilot design formally incorporates
it.

Status remains Partial: the conversion benchmark is resolved, but
curriculum engagement, operational health, and retention remain
unbenchmarked, and the reframed relationship-strain criterion does not
yet exist in any concrete, measurable form.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Age sub-bands and third named competitor restored this cycle — v15
incorrectly flagged both as Unknown/not available; both are present
continuously in `BusinessCase_v6.md` through `v8.md`.**

Children/teens (6-18, sub-banded **6, 7, 8, 9-10, 11-14, 15-18**) — the
end users who complete tasks, earn Mbucks (real-money-pegged) and Mpoints
(cosmetic, non-monetary), and receive education content; minors in the
**15-18 sub-band specifically** are additionally the population eligible
(subject to separate parent opt-in) for the "Fintech Advance" conceptual
course (see Value Proposition, Curriculum Design). Parents/guardians —
who submit the initial budget, assign or approve tasks, set task
earn-rates, assign exam-period bonuses, receive the automated invoice,
execute the real bank payment via their own banking app, mark payments
complete (subject to the minor's accept/dispute step), decide which tasks
require photo-proof, adjudicate disputes within a 48-hour window, are the
subscription purchaser who unlocks additional features (3+ minors,
additional content, Fintech Advance), and are the sole gate for any
minor's access to the app in any form, and the sole, separate gate for
enabling Fintech Advance access for an eligible 15-18 minor. The app
operator (Masood / MiniMoney) — owns the platform, curriculum content,
and invoice/payslip-generation logic, but not the payment rail itself.
The South African Information Regulator (POPIA enforcement) and the
Advertising Regulatory Board (ARB), whose Code of Advertising Practice
Clause 14 governs advertising directed at or exposed to children,
relevant if any ad-supported monetization is pursued post-launch (V2).

**Three named competitor/adjacent-market stakeholders**, all restored
from `BusinessCase_v6.md`: **African Bank (MyWORLD Power Pocket)** — kids'
sub-accounts with debit cards under a parent account, a banking feature
rather than education-led, confirmed to carry no monthly fee;
**MoneyAfrica Kids** — Nigerian-origin edtech app, courses/quizzes,
parent-subscribes-child model, pan-African not SA-specific; and
**MoneyTime SA** — web-based financial literacy curriculum, ages 10-15,
sold B2B2C through schools at R995/year. Apple/Google are app-store
platform stakeholders (Kids Category, Families Policy).

A minor cannot register, or have any data processed, without a parent
acting as registration custodian from the outset (reaffirmed at v14,
after a narrow v12 carve-out was tried and reverted) — this has been the
case's standing design since v5 and remains so; the parent's role as
registration custodian is not a peripheral detail but the entry point for
every other stakeholder relationship in the product.

**Stakeholder relationship introduced at v14:** where a parent opts into
the now-optional account-linking feature (Stitch/Mono-style, read-only),
the linking aggregator itself becomes an additional data-processor/
controller stakeholder sitting between MiniMoney and the parent's own
bank — per `ResearchFindings_v2.md` Item 1, this relationship introduces
its own consent-flow, credential-handling, and data-sharing-agreement
obligations under POPIA's "operator" (processor) provisions, distinct
from and additional to MiniMoney's existing direct obligations. This
applies only to parents who opt in; the honor-system default introduces
no such third party. The parent's own bank remains an unaddressed direct
stakeholder for the honor-system default path.

A child-development/age-appropriateness reviewer, required since v9 to
assess the late-penalty mechanic, remains a stakeholder-adjacent expert
voice this venture has not yet engaged (see Risks, Validation Strategy).
A future AI mediator feature for dispute resolution remains explicitly
out of current scope.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Children/teens **6-18, sub-banded 6, 7, 8, 9-10, 11-14, 15-18** (restored
this cycle — this boundary detail was incorrectly flagged Unknown in v15;
it is present in `BusinessCase_v6.md` through `v8.md`) and their
parents/guardians, in South Africa, on Android at launch (iOS planned as
future work — Android's addressable-market sufficiency is substantiated
by Statcounter's [Certain] 76.74% South African mobile OS share, May
2026, versus 23.24% for iOS; this is traffic share, not population share,
and skews toward higher-usage/urban devices, but is a reasonable proxy
that an Android-first launch reaches the large majority of the reachable
market). A minor is not an independently reachable user: every child
account requires a parent acting as registration custodian from the
outset, and the product is functionally sold to, and accessed through,
the parent first. This was reaffirmed at v14 after a narrow, since-
reverted v12 exception; the case's target-user model has not otherwise
changed since v8. The subscription model implies free-tier-equivalent
access to core features (budget setup, single minor, base education) for
all parents, with paying parents unlocking additional features (3+
minors, additional content, Fintech Advance); real-money in-app purchase
is confirmed parent-only.

No clarification or research finding between v10 and v14 revisits
segmentation, geography, or platform targeting directly. Status remains
Partial: the target population is clearly named, but no market-sizing,
persona-level detail, or segment-specific acquisition data exists beyond
what is captured in Market & Competition and the funnel figures in
Objectives.

## Value Proposition

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

For parents: an automated system that turns household tasks into a
structured payroll-like experience with a built-in financial literacy
curriculum, and — since v14 — an optional, parent-controlled way
(account-linking) to add automated verification on top of the default
honor-system self-report. For children: a "real job" simulation paid out
via the parent's own bank transfer, tied to age-appropriate lessons,
alongside a separate cosmetic-reward system (Mpoints). Since
`Clarifications_v10.md`'s late-penalty redesign, the child-facing value
proposition is purely additive — earning, lessons, and cosmetic rewards —
with no penalty-side friction visible to the child at all; the
escalating late-penalty is a parent-only administrative matter.

**Subscription price point — resolved.** `Clarifications_v10.md`:
"for the subscription it will start at R59.99 a month which will allow
upto 4 kids per family." This is Verified-tier evidence (direct user
confirmation), and it is the fact that closes the v9 gap the Investment
Committee flagged as the most direct blocker to modeling this venture's
value proposition and unit economics. MoneyTime SA's R995/year (25%
sibling discount) remains the only other South African price anchor in
this case, and — expressed monthly (≈R82.92/month, before its own sibling
discount) — sits above MiniMoney's R59.99/month, consistent with the
earlier flag that MoneyTime SA's price likely represented an under-anchor
for a lighter-weight product rather than a ceiling MiniMoney needed to
match.

**Free/Subscription feature table — restored this cycle.** This table was
present in full in `BusinessCase_v8.md` (reflecting the subscription-only
monetization decision made at that version) and its content was already
established in `BusinessCase_v6.md`/`v7.md` under the earlier
Freemium/Paywall framing. `BusinessCase_v9.md` collapsed the section to
"unchanged from v8" without reproducing it, and no version since —
including v15 — restored the actual table content, only the fact that it
existed. Nothing in any later clarification changed which features sit
behind the subscription boundary; only the monetization label itself
changed (Freemium/ads → subscription-only, at v8), which is why the
column headers below read "Free/Subscription" rather than v6's original
"Freemium/Paywall":

| Feature | Free | Subscription |
| - | - | - |
| Setting up a budget | X | X |
| Adding minor | X | X |
| Adding 3+ minors |  | X |
| Access to education | X | X |
| Additional content (expert videos, interactive content) |  | X |
| Enrolling a 15-18 minor for "Fintech Advance" |  | X — **and** requires separate explicit parent opt-in |

**"Fintech Advance" — full description restored this cycle.** This
content was fully scoped at v6 (`Clarifications_v6.md`) and is present
through `BusinessCase_v8.md`'s Curriculum Design section (in
increasingly condensed form) before disappearing as a full description
after v9. It is a distinct, higher-tier curriculum element exclusive to
the **15-18 age sub-band only** — not available to any younger band, even
under the subscription tier. Its pedagogical content is explicitly
**conceptual/educational only**: it teaches the concepts of trending/
entrepreneurial ventures such as **forex trading and dropshipping**, and
does **not** enable any in-app trading execution, brokerage functionality,
or real-money trading activity of any kind. It is gated behind **explicit
parent opt-in specifically for this course**, separate from and in
addition to the general subscription unlock — reaching the subscription
tier and having an eligible 15-18 minor does not automatically grant
access. The user has described Fintech Advance as a **"non-negotiable
requirement"** for that age band's curriculum. This dual gating
(subscription tier + separate parent opt-in) resolves what would
otherwise be a significant undefined risk — teaching real trading
concepts to minors who are simultaneously earning and transacting in a
real-money-pegged in-app currency — into a materially narrower,
better-governed feature. No specialist review has assessed whether this
conceptual content itself requires any additional disclosure or
age-appropriateness review beyond the general POPIA/ARB considerations
already documented (see Legal & Compliance, Risks) — this remains a
genuinely open, narrow question, not a closed one.

**Confidence raised to High this cycle.** v15 held Confidence at Medium
specifically because of "this residual gap" — the missing feature-
boundary detail. With the table and the Fintech Advance description now
restored (both Verified-tier: a direct user hand-edit, scoped by
`Clarifications_v6.md`, unmodified in substance by the later
subscription-only decision), no gap remains that was previously holding
Confidence below High.

Status remains **Complete**: the specific gap that kept this section
Partial through v8 — the missing price point — was resolved by direct
user confirmation at v10, and this cycle's restoration closes a
completeness gap in the section's own body text, not a substantive one.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Fully restored this cycle from `BusinessCase_v6.md`.** This section was
already reduced to "see v7 for full detail" by `BusinessCase_v8.md`,
meaning `v9.md` was never a complete baseline for it — v15's
reconstruction, which could only access `v9.md` and later, inherited a
real, avoidable gap. The content below traces back to `v6.md`, the
richest version, reconciled with the now-resolved subscription-only
conversion rate (v8) and combined with the international-comparables
research (`ResearchFindings_v2.md`) already correctly incorporated at
v15.

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
broader household access (shared device, parent's phone) is plausibly
75-85% for the 6-18 band, but this is a bounded guess, not a stat.

**OS split:** [Certain] Android holds 76.74% of mobile OS share in South
Africa as of May 2026 (Statcounter), iOS 23.24%. This is traffic share,
not population share, and skews toward higher-usage/urban devices, but is
a reasonable proxy indicating an Android-first launch reaches the large
majority of the reachable market.

**Parent financial-app engagement (the real gate):** [Likely] SARB's
Payments Study (SCPC/DCPC, 2023, adults 18+, national population base
40.5M) found 50.3% of South African adults use banking apps regularly —
more than internet banking (27%) but well short of universal. [Guessing]
Parents of school-age kids skew toward the economically active 25-54
bracket, more banked/app-literate than the national average — a
reasonable adjustment is **55-65% banking-app engagement** for this
specific parent cohort, not the raw 50.3% national figure.

**Reachable-market funnel:** 14.5M kids × ~70% device access × ~60%
parent digital-financial engagement ≈ **6.1M kids in "reachable"
households** (device present, parent already comfortable transacting
digitally) — this is the realistic Serviceable Addressable Market, not
the 14.5M Total Addressable Market.

**Adoption rate (the least-evidenced figure in the chain):** [Guessing]
No public South African benchmark exists for kids'-financial-education-
app adoption specifically — confirmed, not merely believed, as a genuine
gap unclosable by further desk research (`ResearchFindings_v1.md` Item
1); this is inference from adjacent markets (GoHenry/Greenlight UK/US),
not South African data: a new entrant with no bank/school distribution
typically captures 0.3-1% of its reachable pool as installs in year one.
Free-to-paid conversion for freemium/subscription kids'-finance apps
benchmarks 2-6% globally; South Africa's lower discretionary income for a
"nice-to-have" app argues for the low end — **1-3%**, the range now
confirmed applicable given the resolved subscription-only monetization
decision (the 2-4% ads-hybrid range cited in earlier versions is no
longer the applicable benchmark).

**Rerun funnel:** ≈6.1M reachable kids × 0.3-1% Year-1 install capture ≈
**18,000-61,000 free users**. Applying the now-resolved 1-3%
subscription-only conversion range ≈ **180-1,830 paying subscribers in
Year 1**. This is lower than the 360-2,440 figure cited elsewhere in this
case's history, which was derived under the earlier, now-superseded 2-4%
ads-hybrid assumption; **this unreconciled subscriber-count discrepancy
remains an open item** (see Revenue & Costs, Financial Considerations,
Outstanding Questions) — restoring this section's full derivation
clarifies *where* the two figures come from without resolving *which* is
current. Landing a distribution partnership (school, bank, telco bundle)
is flagged by the user as the actual lever to move this materially, not
organic install rate.

**Competition in South Africa specifically:** no direct incumbent does
exactly what MiniMoney does (gamified, standalone, mobile-native, direct-
to-parent-distribution consumer app). **Three named local players**, each
missing at least one defining dimension:

- **African Bank's MyWORLD Power Pocket** — kids' sub-accounts with debit
  cards under a parent account; a banking feature, not education-led;
  confirmed to carry no monthly fee (a free sub-account add-on), setting
  a "zero price" anchor in the same market for a banking-feature
  alternative — relevant context for parent price sensitivity even though
  not a direct product comparable.
- **MoneyAfrica Kids** — Nigerian-origin edtech app, courses/quizzes,
  parent-subscribes-child model; available but not built for South
  Africa; shows 10,000+ Google Play downloads and 3,000+ Apple downloads
  (pan-African, not SA-specific, thin review base on Apple's side); its
  premium price remains unpublished/unknown.
- **MoneyTime SA** — web-based financial literacy curriculum, ages 10-15,
  sold B2B2C through schools at R995/year (25% sibling discount); claims
  over 1,500 schools and 130,000 students reached (self-published, not
  independently audited).

None combine gamification + mobile-native + direct-to-parent distribution
the way GoHenry/Greenlight do in the US/UK — a real, evidenced gap — but
it also means there is no local comparable data to validate willingness-
to-pay against.

**International comparables** (`ResearchFindings_v2.md` Item 3, carried
from v15) split into two structurally different approaches. **GoHenry**
(recently folded into Acorns Early) and **Greenlight** solve payment-
verification by becoming the money-mover themselves — issuing their own
prepaid card and holding/moving funds under card-issuing/e-money
licensing, a materially different regulatory posture than MiniMoney's
deliberately non-custodial design. **FamZoo** (IOU-accounts feature) and
**Bomad** ("Bank of Mom and Dad") are closer structural analogs to
MiniMoney: both are track-only, honor-system products with no bank
integration, confirming that MiniMoney's chosen model has precedent
elsewhere and is not a category outlier. No South-Africa-specific
comparable to FamZoo or Bomad was found — the same local-market evidence
gap flagged in `ResearchFindings_v1.md`'s Engagement 1.

**What remains genuinely unresearched:** no pricing benchmark for a
comparable South African product exists beyond MoneyTime SA's R995/year
and the general global freemium/subscription conversion ranges cited
above; no direct demand signal (waitlist, survey, pilot interest) has
been collected specifically for MiniMoney beyond the bounded n=10
interview round (see Problem); the adoption-rate figures remain
explicitly [Guessing]-tagged extrapolations from non-South African
markets, not South African data.

Status remains Partial: the competitive landscape and market-sizing
derivation are now fully documented with three named competitors and a
transparent funnel calculation, but no structured market-share,
pricing-elasticity, or head-to-head feature comparison exists, and the
most decision-relevant figures (Year-1 adoption, conversion rate) remain
the user's own labeled lowest-confidence estimates, not sourced facts.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Structure confirmed and monetization-resolved (subscription-only at
launch, ads deferred to V2); R59.99/month, up to 4 children per family —
see Value Proposition for the full Free/Subscription feature table,
restored this cycle. MiniMoney is a facilitation/education layer that
sits on top of the parent's own bank account and does not move or hold
funds, removing the need for a money-transmitter license as a primary
business-model constraint (subject to specialist confirmation — see Legal
& Compliance). Optional account-linking is a trust/verification feature
within the existing subscription model, not a new revenue line — it gives
parents who opt in an additional, automated way to verify a child's
earnings claim, alongside the existing honor-system self-report default,
and is gated behind the specialist legal opinion before it can ship. If
pursued post-launch, advertising remains framed as a partial CAC-offset/
subscription-cost-reduction lever, not a standalone revenue pillar; POPIA
Section 34 and ARB Clause 14 jointly restrict any future ad layer to
contextual, non-profiled inventory (see Legal & Compliance). The
Mpoints/Apple IAP-currency question remains unresolved.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Candidate cost categories:** (1) engineering/build cost — the
engineering-cost range ($25,000-$40,000 MVP; $60,000-$120,000+ full
build, from five converging agency-quote estimates) is reconciled *in
kind*, not *in amount*, against the solopreneur/AI-assisted production
model described in Constraints — the two figures price different things
(agency-priced labor cost vs. founder-time timeline). No budget ceiling
exists for the "external expertise on-demand" line, so how much of the
agency range this approach actually displaces remains open. (2)
Curriculum content production cost — likely the largest recurring cost if
age-banded content requiring periodic updates is needed, including the
Fintech Advance course for the 15-18 band specifically. (3) Customer
acquisition cost (CAC) — a new entrant with no bank/school distribution
typically captures 0.3-1% of its reachable pool as Year-1 installs
organically (see Market & Competition); a distribution partnership
(school, bank, telco bundle) is flagged as the actual lever to move this
materially; no absolute Rand/USD CAC figure is available. (4) Legal/
compliance cost — a firm shortlist (Caveat Legal, VeraSafe, PPM
Attorneys, Bregman Moodley Attorneys, MJ Kotze Inc) and a scoping
estimate (R25,000-R80,000, explicitly Research House's own inference, not
a quote) exist for the still-unobtained specialist opinion.

**Candidate revenue framing:** Revenue = (active subscribing parent
accounts) × R59.99/month, up to 4 children per family. Using Market &
Competition's restored funnel derivation: 18,000-61,000 Year-1 free
installs, and — applying the now-resolved 1-3% subscription-only
conversion range — **180-1,830 Year-1 paying subscribers**, computed
directly in this cycle's Market & Competition restoration. This sits
below the **360-2,440** figure cited elsewhere in the case's history
(derived under the earlier, superseded 2-4% ads-hybrid assumption). **The
unreconciled subscriber-count discrepancy (180-1,830 computed vs.
360-2,440 cited) remains open** — restoring the derivation this cycle
clarifies its origin without resolving which figure the business should
plan against (see Outstanding Questions). Ad revenue, if pursued
post-launch, is explicitly framed as a partial CAC offset, not a
standalone second revenue line, and should not be modeled as material
incremental revenue.

## Operations

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

**Budget and earning mechanics:** the parent submits a budget setting the
minor's "basic income"; task earn-rates are derived from this budget
either as a percentage or a parent-set fixed Mbuck amount (minimum 1
Mbuck per task). Every completed task separately earns a flat 10
Mpoints. **Task structure:** predefined and custom parent-created tasks,
recurring monthly/weekly/daily. **Bonus mechanic:** a parent-configured
Mbuck bonus scaled to exam-period academic improvement (example: 6
subjects averaging 65%; every 5% improvement earns 5 Mbucks, capping at
15 Mbucks for 15%+ improvement). **Completion, verification, and
reporting flow:** minor marks complete, parent notified, optional
live-camera photo-proof (gallery photos not accepted), weekly summary
report to both. **Dispute mechanism:** parent may decline within a
48-hour window; beyond that, "the parent and minor need to compromise" —
no formal enforced resolution mechanism exists; a future, explicitly
out-of-scope AI-mediator feature is planned. **Payment confirmation and
enforcement:** because payment happens via the parent's own banking app,
outside MiniMoney, the app cannot technically verify payment occurred;
the parent marks payment complete, the minor accepts or disputes.

**Late-penalty mechanic — parent-only, child-invisible, per
`Clarifications_v10.md`'s final redesign (supersedes every earlier
version's description):** the escalating late-penalty (5→6→7 Mbucks/week,
pilot cap 3) is incurred entirely by the parent, not the child. The child
has **no visibility whatsoever** into whether a penalty was charged or
how much is owed — this is purely a parent-side administrative/financial
matter, invisible to the minor's account, UI, statements, or reports.
This redesign also raises a consistency question, flagged but not
resolved by any input available to this case: the previously-described
"request for payment" prompt feature (minors generate a payment-request
prompt after month 1, and monthly thereafter while arrears are unsettled)
assumed child visibility into arrears — whether this feature remains
coherent, is removed, or is redesigned under the new no-visibility model
is an open item (see Outstanding Questions).

**Optional account-linking's operational opt-in flow** (where in the
parent flow it is offered, what consent language is shown, how a parent
later un-links) is undocumented and remains an open item. A residual
ambiguity is flagged, not resolved: whether a distinct post-registration,
pre-budget-link stage still exists within the now fully parent-supervised
flow.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

A mobile app, Android confirmed as primary launch platform, iOS as future
porting work. Required components: budget-setting flow; task-assignment
engine (predefined and custom tasks, monthly/weekly/daily recurrence); a
dual-currency ledger separating Mbucks (real-money-pegged, minimum 1 per
task) from Mpoints (flat 10 per completed task, cosmetic-store-only); an
exam-performance bonus calculator; a notification system; weekly
report-generation; direct camera-app invocation for photo-proof; a
48-hour dispute-window workflow; a payment-accept/dispute workflow; an
arrears/late-penalty calculator with escalating weekly rates (5→6→7,
pilot cap 3), now scoped to be visible only to the parent, per the v10
redesign; document generation (invoice for parent, payslip for child); no
banking-rail integration for the honor-system default path; a
feature-entitlement/subscription-gating system, including a distinct
entitlement flag for Fintech Advance gated by two independent conditions
(the subscription tier AND a separate explicit parent opt-in) plus an
age-band check restricting Fintech Advance to the 15-18 sub-band only. A
single universal consent gate (parent account, consent recorded, before
any minor access of any kind) is sufficient; no two-mode account
architecture is needed.

Optional read-only account-linking is a Stitch/Mono-style API integration
dependency, parent-opt-in only, gated behind the specialist legal opinion.
Honor-system self-report remains the default technical path requiring no
external integration. No technology-stack detail for the linking
integration itself has been specified in any input available to this
case. What remains unspecified: exactly how "linking" a child account to
a parent account is technically initiated; how payment confirmation is
captured beyond the accept/dispute UI; technical specifics of the
exam-bonus grade-input mechanism.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The specialist POPIA/ARB/contract-law legal opinion remains unobtained.
MiniMoney does not hold, move, or take custody of funds. Initial launch
jurisdiction is South Africa, governed by POPIA. The pre-link
independent-registration carve-out is resolved by removal (v14), which
closes the specific scenario that likely triggered POPIA's Section 34/35
consent requirement at registration — a genuine structural risk
elimination, not merely a Confidence-improving clarification.

**Read-only account-linking** is now optional rather than excluded; the
underlying NCR question (does the NCR reach a read-only, non-custodial
service) remains unresolved by desk research (`ResearchFindings_v3.md`
Item 2: none of the NCR's four registration categories plausibly fits,
but this is a reasoned inference, not a regulator statement) and now
gates a single shippable optional feature rather than justifying a
permanent exclusion.

**Contractual/legal enforceability of the arrears balance**
(`ResearchFindings_v2.md` Item 2): South African contract law's
domestic-agreement presumption (illustrated by *Balfour v Balfour*, a
foundational common-law doctrine broadly recognized in South Africa,
though no SA case law applying it to a parent-child allowance/penalty
arrangement specifically was found) presumes family arrangements are not
intended to be legally binding, rebuttable only with clear evidence
otherwise; whether MiniMoney's "agreed condition of the budget setup"
framing overcomes this presumption is unconfirmed. Minors (age 7-18) have
only limited contractual capacity in South Africa; the penalty runs
against the parent, not the child, which sidesteps the minor-capacity
question for the penalty itself, but the underlying payslip amount owed
to the child likely still sits inside this same limited-capacity
framework. The National Credit Act is confirmed inapplicable to this kind
of informal, non-interest-bearing family arrangement.

**POPIA Section 34** requires consent from a "competent person" before
processing a child's personal information at all, reinforcing the
universal-consent-gate design. **ARB Code of Advertising Practice Clause
14** prohibits ads that exploit children's credulity or inexperience —
relevant to any post-launch V2 advertising, not a launch-blocking item.
**POPIA Section 14** (retention) is confirmed as statutory text; no
child-specific supplementary retention rule (comparable to COPPA or
GDPR-K) exists within POPIA itself — the user has explicitly accepted the
risk that the general principle is sufficient without such rules, pending
specialist confirmation.

**Fintech Advance content risk:** because the course is explicitly
conceptual/educational only, with no in-app trading execution, brokerage
functionality, or real-money trading activity, this substantially
narrows — though does not entirely eliminate — a candidate concern about
financial-promotion-adjacent content being served to minors. The dual
gating (subscription tier + separate explicit parent opt-in) further
reduces this risk. No specialist review has assessed whether educational
content describing speculative trading activities, even without
execution capability, triggers any advertising-to-minors or
financial-education-content rule beyond the general POPIA/ARB
considerations above — a new, narrow, but unresolved question.

Minor contractual capacity, the domestic-agreement presumption, and the
absence of ARB/NCR precedent for "payslip"/"invoice"/"late penalty"
terminology applied to minors remain untouched, unresolved items.
Confidence holds flat at Medium, bounded by these untouched items, not by
anything resolved this cycle. The feature-level build-gating plan
established at v9 (financial-trigger features locked behind the opinion;
foundational rails may proceed in parallel) remains in force, with
optional account-linking added to it as a gated item.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Three risk categories restored this cycle** — present continuously in
`BusinessCase_v6.md` through `v9.md`, silently dropped from the summary
list somewhere between v10 and v13 (v14 explicitly flagged it could not
see v13's full risk register; this cycle's access to v9's full text
resolves that visibility gap): dispute-escalation risk, advertising/
child-data risk, and Fintech Advance content risk. All three are restored
below, reconciled with every later decision that touched them.

- **Regulatory risk (Critical):** the invoice/payment-trigger/late-
  penalty/terminology mechanics could still be characterized as
  money-transmission-adjacent or otherwise regulated; no ARB/NCR
  precedent exists.
- **Child-safety/data-privacy risk (Critical, partly risk-accepted):**
  the pre-link carve-out risk is resolved by removal (v14); two explicit
  risk-accepted assumptions (POPIA Section 14 retention sufficiency;
  exam-bonus mechanic's no-schools-data-privacy-dimension) remain
  unverified by any external authority.
- **Trust/enforcement risk (reframed):** the "foregone opportunity"
  framing around account-linking is resolved since the feature is no
  longer excluded, but the feature itself cannot ship until the
  specialist opinion clears the NCR question; the honor-system default
  carries whatever enforcement-trust limitations it already had.
- **Late-penalty/relationship risk (narrowed, not eliminated):** the
  penalty is now parent-only and child-invisible (v10), substantially
  narrowing the direct child-facing version of this risk, though a
  parent's own stress or behavior around an accumulating, child-invisible
  obligation could still indirectly affect the child (see Success
  Criteria).
- **Dispute-escalation risk (restored, unresolved):** the described
  dispute process beyond the 48-hour window has no formal resolution
  mechanism in current scope ("the parent and minor need to compromise");
  families without an effective informal compromise mechanism have no
  in-app recourse.
- **Terminology/perception risk:** framing a child's allowance as
  "payslip," "overtime," "expenses," "late penalty," and "arrears" could
  raise concerns among child psychologists or regulators about
  normalizing labor-like or debt-like relationships between parent and
  child; confirmed, not merely hypothesized, that no ARB/NCR precedent
  addresses this exact terminology applied to minors.
- **Advertising/child-data risk (restored, reduced near-term relevance):**
  if a post-launch V2 ads-supported path is pursued, POPIA Section 34 and
  ARB Clause 14 jointly restrict any ad-targeting approach to contextual,
  non-profiled inventory; since ads are deferred and not a launch feature,
  this is not an immediate launch-blocking concern.
- **Fintech Advance content risk (restored, narrowed but not
  eliminated):** teaching conceptual forex-trading and entrepreneurial-
  venture content to 15-18-year-olds, even without in-app execution
  capability, carries residual risk of being perceived as normalizing
  speculative financial activity to minors; the dual gating and explicit
  exclusion of trading execution substantially narrow this risk, but no
  specialist has reviewed whether the conceptual content itself requires
  additional disclosure or age-appropriateness review.
- **Child-development/age-appropriateness risk (named at v9):** the
  late-penalty mechanic's design has changed (parent-only,
  child-invisible), narrowing but not eliminating this risk; the required
  expert review has still not been commissioned.
- **Competitive risk:** three named South African competitors exist,
  none combining MiniMoney's exact mechanic — a real, evidenced gap, but
  one that also means no local pricing/adoption comparable exists.
- **Monetization-execution risk (narrowed):** subscription-only decided;
  remaining execution risk is limited to conversion-rate validation.
- **App-store policy risk:** the Mpoints cosmetic store aimed at children
  may be subject to child-directed-app design and disclosure requirements
  on both platforms; Apple's Kids Category age bands (topping out at
  9-11) appear structurally incompatible with MiniMoney's 6-18 span for
  any future iOS port.
- **Platform-concentration risk (narrowed, evidence-backed):** Android's
  76.74% South African mobile OS share meaningfully de-risks the
  Android-only launch decision, though the 23.24% iOS share represents a
  real, non-trivial excluded segment at launch.
- **Adoption/forecasting risk:** the Year-1 adoption and conversion
  figures underpinning the funnel model are explicitly [Guessing]-tagged
  extrapolations from non-South-African markets, confirmed unclosable by
  further desk research; should be treated as a planning range, not a
  forecast.
- **Engineering-cost estimation risk:** the two-tier build-cost range is
  sourced from development-agency marketing pages with an inherent
  incentive to anchor toward their own typical project size, and has not
  been checked against MiniMoney's actual feature spec via real quotes.
- **Legal-opinion-deferral risk (sharpened):** the opinion's required
  scope has been narrowed across six consecutive revisions (v10 through
  v15) without being commissioned.
- **Account-linking regulatory-gate risk (introduced v14):** the feature
  cannot ship until the specialist opinion clears the NCR question; the
  honor-system default is unaffected and proceeds regardless.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parent-direct payment; SA launch jurisdiction; universal consent gate (no
exceptions, as of v14); Android-first; Mbucks/Mpoints dual currency;
7-Mbuck cap with 3-Mbuck pilot cap; the two explicit POPIA/exam-bonus
risk acceptances; the fixed Mbucks-to-Rand peg; the late-penalty
mechanic's nature as a parent-only administrative matter, invisible to
the child; the exam-performance bonus mechanic's grade data is
self-reported/parent-entered, with no school-system integration; the app
is intended primarily as a South African B2C product at launch. The
NCR-avoidance premise underlying the original Stitch/Mono exclusion is
decoupled from the current product decision (linking is now optional
regardless of how that question resolves) but remains itself unconfirmed.
The v12/v13 assumption about the pre-link carve-out's POPIA posture is
moot, superseded by its v14 removal, retained for audit-trail continuity
only.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Solopreneur venture; AI-assisted ("vibe coding") development; external
technical expertise engaged only on-demand, for scoped, harder problems
the founder cannot resolve alone (the specialist legal opinion is one
clear example, already costed separately at R25,000-R80,000);
directional ~3-month build timeline; deliberately non-granular by the
user's own stated preference. Platform choice (Android primary, iOS
future) is confirmed and substantiated by Statcounter data. Status
remains Complete for the same reason it has since v8 — the section's
central question ("what company-side budget, timeline, and team size are
available?") has been answered in the terms the user chose to answer it
in — even though this qualitative characterization does not, by itself,
resolve how much of the separately-sourced $25,000-$120,000+ agency-cost
range the solopreneur/AI-assisted approach actually displaces (see
Revenue & Costs).

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Foundational, non-financial rails (UI shell, task-assignment engine,
curriculum content, budget-input capture, consent-gate scaffolding) may
proceed under the solopreneur/AI-assisted build immediately;
financial-trigger features (invoice generation, payment-confirmation
workflow, late-penalty/arrears calculation, data-retention pipeline, and
now optional account-linking) may not ship to real users until the
specialist legal opinion — or, at minimum, the recommended preliminary
legal read — has been obtained. The opinion's commissioning trigger
remains event-based ("once a stable working model exists, and before any
pilot testing with real families begins," per `Clarifications_v10.md`),
a point this Incubator has repeatedly flagged, without prescribing a
decision, as worth reconsidering in favor of a dated trigger, now that
six consecutive revisions have narrowed the opinion's required scope
without commissioning it.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

No funding ask, runway, or full numeric financial projections exist. The
subscription price (R59.99/month, up to 4 children per family) is now
known and modeled against the Year-1 funnel range (see Market &
Competition, restored this cycle, for the full derivation): 180-1,830
paying subscribers under the now-resolved 1-3% subscription-only
conversion range. The family-vs-child install-count ambiguity (does the
funnel range count families or individual children?) remains unresolved
— checked against the now-removed pre-link carve-out as a possible
contributing cause per `Clarifications_v14.md`'s prompt, but this
Incubator's available inputs cannot confirm or rule out that connection.
The unreconciled subscriber-count discrepancy (180-1,830 computed vs.
360-2,440 cited, the latter derived under the superseded 2-4% ads-hybrid
assumption) remains open.

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Legal validation (opinion's required scope narrower, still unobtained);
primary user-research validation (n=10 bound, unchanged); child-
development/age-appropriateness review (still required, not yet
commissioned); trust/enforcement and dispute-mechanism validation (now
also covering whether parents actually opt into account-linking and
whether it measurably improves trust outcomes); market/demand validation
(commissioned survey, R80,000-R250,000, 3-6 weeks, or a live pilot);
pricing/conversion validation (price now known, conversion still
unvalidated); curriculum validation (unchanged, still generic — see
Curriculum Design below); account-linking feature validation (requires
both specialist legal confirmation and a designed, reviewed opt-in
consent flow, neither of which exists yet).

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

The n=10 first-party interview data point (bounded, non-representative,
per standing instruction); `ResearchFindings_v1.md`'s (Engagement 1),
`ResearchFindings_v2.md`'s (Engagement 2), and `ResearchFindings_v3.md`'s
(Engagement 3) vendor engagements, all Supported-tier; the user's
directly-cited South African statutory/statistical sources
(`Clarifications_v6.md`: Stats SA, the 2024 Stellenbosch device-ownership
study, Statcounter, SARB's Payments Study, POPIA Section 34, ARB Clause
14); `Clarifications_v8.md`, `v10.md`, `v11.md`, `v12.md`, and `v14.md`,
each Verified-tier as to what design decision was made, not Verified as
to any underlying legal or market question those decisions merely
reframe rather than resolve.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this cycle (removed from the open list, retained here for
audit-trail continuity):** the identity of the third named competitor
(African Bank's MyWORLD Power Pocket — restored from `BusinessCase_v6.md`,
incorrectly flagged Unknown at v15); the specific free-vs-subscription
feature split (restored table, `BusinessCase_v8.md`, incorrectly flagged
missing at v15); the minors' age sub-band boundaries (6, 7, 8, 9-10,
11-14, 15-18 — restored from `BusinessCase_v6.md`, incorrectly flagged
Unknown at v15).

**Still open:** does the specialist legal opinion confirm or refute NCR
exposure for read-only account-linking; does a distinct post-
registration, pre-budget-link practice stage still exist; the
account-linking opt-in UX flow; the family-vs-child install-count
ambiguity; whether the event-based legal-opinion trigger should become a
dated one; the subscriber-count discrepancy (180-1,830 computed vs.
360-2,440 cited); the preliminary legal read's adoption decision; fund
custody mechanics; task verification; dispute-escalation beyond 48 hours;
payment-routing timeline; late-penalty cap rationale; whether the
"request for payment" prompt feature remains coherent now that the child
has zero visibility into arrears (restored open item, `Clarifications_v10.md`);
exam-bonus data source; Mbucks-peg flexibility; curriculum age-band
splits, instructional format, standards alignment, and content
authorship (see Curriculum Design); app-store policy sub-questions;
MoneyAfrica Kids' unpublished premium price; whether informal
engineering-cost quotes will be sought; the external-help budget ceiling;
the schools-partnership channel's timeline/target school count/resourcing
plan; the domestic-agreement presumption's application to MiniMoney's
"agreed condition of budget setup" framing; South Africa-specific vendor
pricing for Stitch's or Mono's account-linking product (no SA-specific
quote found — a direct sales inquiry to both vendors is the only way to
get a firm number, per `ResearchFindings_v2.md` Item 1).

## Readiness Score

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

Scoring basis: Complete = 5 pts, Partial = 2 pts, Incomplete = 0 pts.
Critical sections (marked ★) are double-weighted. Recomputed in full
against this cycle's fully reconstructed document.

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
| Operations | Complete | 1x | 5 |
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

Points earned: **67**.

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130.**

**Readiness Score = 67 / 130 = 51.5%, rounded to 52%. Confirmed unchanged
from v15.** Every section's Status in this recomputation matches
`BusinessCase_v15.md`'s own scoring table exactly — this cycle restored
substantive content (and, in two cases, corrected Confidence tags) but
did not change any section's Status, since every restoration closed an
evidentiary gap (content that existed but was not reproduced), not a
substantive one (an open question the user has not yet answered).

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → 52% (v14) → 52% (v15) → **52% (v16, second consolidation
cycle — no Status changed; Value Proposition, Curriculum Design, Market &
Competition, Risks, Objectives, Stakeholders, and Target Users/Customers
given fully restored, self-contained substantive text traced against the
complete version history rather than a single assumed-good baseline).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB/contract-law legal opinion remains
   unobtained. Scope covers: domestic-agreement presumption; minor
   contractual capacity; the NCR question, now gating the optional
   account-linking feature specifically. Confidence holds flat at Medium.

2. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions)** — unresolved; checked against the
   now-removed carve-out as a possible cause, inconclusively.

3. **Account-linking regulatory gate (Legal & Compliance, Risks,
   Roadmap)** — the "foregone opportunity" framing is resolved (linking
   is optional, not excluded); the underlying NCR question remains
   unresolved by desk research and gates the feature's ship date.

4. **Child-development/age-appropriateness risk (Success Criteria,
   Risks, Validation Strategy)** — the late-penalty mechanic's design has
   changed (parent-only, child-invisible), narrowing but not eliminating
   this risk; the required expert review has still not been commissioned.

5. **Subscriber-count discrepancy (Revenue & Costs, Market &
   Competition)** — unresolved; this cycle's Market & Competition
   restoration now shows the derivation of both figures (180-1,830 from
   the current 1-3% subscription-only rate; 360-2,440 from the superseded
   2-4% ads-hybrid rate) without resolving which the business should plan
   against.

6. **Market & Competition and Curriculum Design evidentiary thinness —
   RESOLVED in v16, retained for audit-trail continuity.** v15 believed
   these sections' fuller detail was permanently inaccessible beyond
   `BusinessCase_v9.md`. This cycle traced both back to `BusinessCase_v6.md`
   and restored them in full; the content was never actually lost from
   the case's history, only from the documents reproducing it. v15's own
   assumption that v9 was the earliest available baseline was incorrect
   for these sections, and for Value Proposition. Curriculum Design's
   Confidence is restored from Low to Medium accordingly (see What
   Changed, above); Value Proposition's Confidence is raised from Medium
   to High.

7. **"Request for payment" prompt feature coherence (restored open item,
   Operations, Outstanding Questions)** — the v10 late-penalty redesign
   (parent-only, child-invisible) raises an unresolved question about
   whether the pre-existing "request for payment" prompt feature (which
   assumed child visibility into arrears) remains coherent as designed.
   No input available to this case resolves it.

8. **Request-for-payment feature inconsistency (naming carried from prior
   versions) — RESOLVED in v11**, retained for audit-trail continuity.

9. **90-day vs. annual funnel tension — RESOLVED in v10**, retained for
   audit-trail continuity.

10. **Pre-link independent-registration carve-out — RESOLVED in v14 by
    removal**, retained for audit-trail continuity.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

**Fully restored this cycle from `BusinessCase_v6.md`.** This section was
already reduced to a bare pointer by `BusinessCase_v9.md` ("Unchanged
from v8"), and v15's reconstruction, explicit about being unable to
access `v8.md`, could only recover the case study's single sentence and
the section's four named open questions. This cycle's access to the full
version history shows the fuller content was never actually lost — it is
present in full in `BusinessCase_v6.md` and, in condensed form, through
`v8.md`.

*Appended because MiniMoney is an education product for a 12-year age
span (6-18) — the completion gate requires domain-specific sections for
products with curriculum design needs.*

Per the case study (verbatim, `00_CaseStudy.md`): "Education needs to be
incorporated and designed to appeal to the respective age demographic."
**The age floor of 6 is intentional**, to introduce financial literacy
"as early as 6." The curriculum does not need to be a full year's worth
of content, but rather **a short course completable daily or weekly**,
with example mechanics including **(a) differentiating between different
currencies**, and **(b) basic transactions that introduce "word sums" as
a mechanism for the child to derive what remains owed or returned after
paying for goods or services**. MiniMoney's curriculum must span a
12-year age range (6-18) — a substantial instructional-design challenge
given how differently a 6-year-old and an 18-year-old engage with
financial concepts.

**"Fintech Advance"** is a distinct, higher-tier curriculum element
exclusive to the **15-18 sub-band**, teaching the concepts of trending/
entrepreneurial ventures (forex trading, dropshipping) as
**conceptual/educational content only** — explicitly excluding any
in-app trading execution or brokerage functionality — described by the
user as a **"non-negotiable requirement"** for that age band's
curriculum, while access to it for any individual minor remains solely a
parent decision made at the parent's discretion, gated separately from
(in addition to) the general subscription tier that contains it (see
Value Proposition for the full description).

Four items remain named as explicitly unresolved, unaddressed by any
clarification or research finding between v10 and v15:

1. **Age-band curriculum splits** — how the 6-18 range divides into
   distinct instructional tiers (beyond the product-level sub-bands used
   elsewhere for stakeholder/task purposes — see Stakeholders — which are
   not confirmed to be the same as any curriculum-content-tier split) is
   not specified in any available input.
2. **Instructional format** — whether lessons are video, interactive,
   gamified-quiz, text-based, or a mix, beyond "a short daily/weekly
   completable course," is not specified.
3. **Standards alignment** — whether content maps to any South African
   national curriculum (e.g. CAPS) or recognized financial-literacy
   standard is not specified.
4. **Content authorship** — who writes and reviews the curriculum
   (in-house, licensed, or expert-commissioned) is not specified,
   including for Fintech Advance specifically, which the Incubator flags
   may require subject-matter expertise (financial markets education)
   distinct from the general curriculum's authorship needs.

The child-development/age-appropriateness reviewer required since v9 to
assess the late-penalty mechanic (see Risks, Success Criteria) is
adjacent to, but formally distinct from, whatever review this section's
own content would eventually need — one assesses a mechanic's
psychological impact, the other would assess instructional-content
design. Neither has been engaged. The n=10 interview finding that 7 of 10
families were interested specifically in the education aspect (see
Problem) is a modest, directional positive signal for this section, but
resolves none of the four items above.

**Confidence restored from Low to Medium this cycle.** v15 downgraded
this section to Low on the reasoning that its evidentiary base was "one
sentence from the original case study and four named-but-undetailed open
questions." That was an accurate description of what v15's own available
inputs contained, but this cycle's fuller trace shows the actual
evidentiary base was always richer — the age-6 rationale, curriculum
shape, and two example mechanics existed continuously through v6-v8 and
were simply not reproduced from v9 onward. Per Playbook Entry 4, this is
a correction to the prior cycle's assessment, not new, more favorable
information: the four named open items are exactly as unresolved as v15
believed. Status remains Partial: something concrete now exists in full
(the age-6 rationale, the curriculum shape, two example mechanics, the
Fintech Advance scoping), but no age-band splits, instructional format,
standards alignment, or authorship plan has been supplied in any input
available to this case.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Since a minor cannot register, or have any data processed, without a
parent acting as custodian from the outset, the registration-triggers-
POPIA question that drove earlier downgrades can no longer arise in
MiniMoney's actual design; `ResearchFindings_v3.md`'s statutory research
remains valid, sourced research but no longer applies to any live
feature. Confidence is held at Medium, not raised to High, for reasons
unrelated to that resolved question: the technical mechanism for the
(now-universal) consent gate is still undocumented; the two explicit
user risk-accepted assumptions (POPIA Section 14 retention sufficiency;
exam-bonus mechanic's no-schools-data-privacy-dimension assumption)
remain accepted but unreviewed by a specialist; Google Play's Families
Policy loyalty-point disclosure requirement (directly applicable to
Mpoints) and Apple's Kids Category IAP-currency question remain open; the
confirmed absence of ARB/NCR precedent for "payslip"/"invoice"/"late
penalty" terminology applied to minors is unchanged; whether the
Fintech Advance conceptual content itself requires any additional
disclosure or age-appropriateness review beyond the general POPIA/ARB
considerations (see Legal & Compliance, Curriculum Design) remains open.
A residual item remains open: whether a distinct post-registration,
pre-budget-link stage still exists within the now fully parent-supervised
flow, and if so, whether a narrower version of the practice-data-as-
personal-information question persists within it.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 52% (67/130),
  confirmed unchanged from v15 by this cycle's full recomputation.

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

- **No section consists solely of an "Unchanged from vN, not
  reproduced" pointer, and no section's content was accepted as complete
  without being traced to its actual origin in the full version history:**
  **Yes — this cycle's specific mandate.** Value Proposition, Curriculum
  Design, and Market & Competition are restored in full from the earliest
  version where each was last genuinely complete (`v8.md`/`v6.md`,
  `v6.md`, and `v6.md` respectively), not from v9 or v15's own prior
  work. Stakeholders, Target Users/Customers, Objectives, and Risks had
  specific factual errors or drop-outs corrected via the same full-chain
  trace. Every other section was checked against this fuller history and
  found to already contain its full, self-contained substantive text
  with no further restoration required.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
remains 52%, confirmed unchanged by full recomputation — this cycle is a
second completeness and traceability fix, not a new information event,
and does not by itself advance the score. A v17 would need: the actual
specialist legal opinion obtained; resolution of the family-vs-child
install-count and subscriber-count discrepancies; the account-linking
opt-in UX flow documented; the required child-development review
conducted; actual curriculum-design content beyond this cycle's
restoration (age-band splits, instructional format, standards alignment,
authorship); and resolution of the restored "request for payment"
feature-coherence question — to meaningfully advance the Readiness Score
beyond this cycle's completeness-only improvement.
