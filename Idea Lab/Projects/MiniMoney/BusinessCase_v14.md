# Business Case: MiniMoney — v14

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v13.md` (prior version), and
> `Clarifications_v14.md` (two user design decisions made in direct
> response to `BusinessCase_v13.md`'s Critical Gaps #3 and #4). This
> document is self-certified against the Incubator completion gate.
>
> **Input-scope limitation, stated explicitly:** this Incubator's
> authorized inputs for this cycle are `00_CaseStudy.md`,
> `BusinessCase_v13.md`, and `Clarifications_v14.md` only — no earlier
> version (v12 or before) was read. `BusinessCase_v13.md` itself carries
> forward several sections as "Unchanged from v12" pointers, without
> reproducing their full text (a pattern v13 established for the same
> reason relative to v12). Where `Clarifications_v14.md` asks this
> Incubator to check a section for carve-out-dependent language and that
> section's only available text is a v13 pointer with no substantive
> content, this Incubator cannot confirm or rule out carve-out-dependent
> language in the fuller text it has never seen. This is flagged
> per-section below rather than silently treated as "checked, clean."

## What Changed in v14 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

`Clarifications_v14.md` records two direct user design decisions, made in
response to `BusinessCase_v13.md`'s Critical Gaps #3 and #4. Both are
Verified-tier evidence (direct user confirmation, not vendor research or
Incubator inference).

**(1) Pre-link independent-registration carve-out — removed entirely.**
The `Clarifications_v12.md` design (a minor could independently download,
register, and access one practice-only "budgeting" feature before any
parent link existed) is reverted. A minor can no longer register an
account at all without a parent acting as registration custodian — this
restores and reaffirms the universal parental-consent gate established in
`Clarifications_v5.md`. Per the user's own framing and per Playbook Entry
2, this is treated as a **correction** across every section that
described the carve-out, not a supplemented addition. This closes v13
Critical Gap #3 (marked **RESOLVED** below, retained for audit trail per
the precedent already set for Gaps #7 and #8).

**(2) Read-only account-linking (Stitch/Mono) — made optional, not
excluded.** The `Clarifications_v10.md` decision to exclude account-linking
entirely (on an NCR-avoidance rationale that `ResearchFindings_v3.md`
found likely mistaken) is reversed. Account-linking becomes an **optional,
parent-controlled feature** — honor-system self-report remains the
default for parents who decline to link. The user's stated reason is
broader than the now-questioned NCR premise alone: some parents may not
want to link banking data regardless of the regulatory position. The
underlying regulatory question (does the NCR, or any other SA regulator,
reach this kind of service) is **still not definitively resolved** by
desk research and remains gated behind the specialist legal opinion
before this feature ships, per the existing v9 feature-level build-gating
plan.

**Ripple-effect check performed per Playbook Entry 2, with results:**

- **Legal & Compliance / Child Data & Consent (Critical):** substantively
  affected — see below. The registration-triggers-POPIA question is
  rendered moot as a live scenario (there is no longer any registration
  path that precedes parental consent), though other unrelated open items
  in these sections are untouched and Status remains Partial.
- **Risks / Assumptions:** substantively affected — the "foregone
  opportunity" framing of the NCR-avoidance premise (raised in
  `reviews/DevilsAdvocate.md`, v12 Objection 2) is resolved by the feature
  no longer being forgone; the underlying regulatory question is
  reframed from "justifying a permanent exclusion" to "gating a shippable
  optional feature."
- **Operations, Technology, Business Model, Roadmap, Validation
  Strategy:** updated with new content describing the optional
  account-linking feature, per `Clarifications_v14.md`'s explicit
  instruction. This new content is drawn directly from
  `Clarifications_v14.md` and does not require v12's original text.
- **Financial Considerations (family-vs-child install-count ambiguity):**
  checked, **not resolved — flagged as an input-scope limitation.** It is
  plausible the carve-out contributed to this ambiguity (an
  independently-registered minor install may have been counted separately
  from a "family" install), but it is equally plausible the ambiguity is
  driven entirely by the up-to-4-children-per-family subscription
  structure, unrelated to the carve-out. This Incubator's available
  inputs do not contain the original computation detail needed to
  distinguish these, so this is **not** claimed as resolved. See
  Outstanding Questions.
- **Executive Summary's platform/feature description:** substantively
  affected — rewritten below.
- **Stakeholders, Target Users/Customers, Value Proposition, Technology
  (pre-existing text only):** `BusinessCase_v13.md` carries these forward
  as bare "Unchanged from v12" pointers with no substantive carve-out
  language visible to this Incubator. **This Incubator cannot confirm
  these sections are clean of carve-out-dependent language it has never
  read** — flagged explicitly as a limitation, not certified as checked.

**Net effect on Readiness Score: none.** No section's Status transitions
this cycle. Consistent with Playbook Entry 1, this is stated explicitly:
the two decisions incorporated this cycle are substantive product-design
changes, not mere analytical fixes, and they do close a full Critical Gap
(#3) — but because the Status-only Readiness Score rubric does not
directly credit gap-count reduction, and because Legal & Compliance and
Child Data & Consent remain Partial (still gated by unrelated,
untouched items — contractual capacity, domestic-agreement presumption,
ARB precedent absence, the still-open NCR question now attached to the
optional account-linking feature), the score holds at the same figure as
v13. **Readiness Score: 67/130 = 51.5%, rounded to 52%, unchanged from
v13.** Per Playbook Entry 3, this flat score should not be read as "no
progress" — a full Critical Gap closed this cycle and a DevilsAdvocate
objection was substantively resolved — but the Status-based rubric does
not surface that on its own, so it is stated here explicitly.

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
purchases remain parent-only. The late-payment penalty mechanic is
incurred entirely by the parent (5→6→7 Mbucks/week, pilot cap 3); the
child has zero visibility into it.

**A minor cannot register an account, nor access any part of the app,
without a parent acting as registration custodian from the outset.** This
revision removes the `Clarifications_v12.md` pre-link
independent-registration carve-out entirely — the narrow exception that
had allowed a minor to independently register and access a practice-only
budgeting feature before any parent link existed. This reverts the case
to, and reaffirms, the universal parental-consent gate established in
`Clarifications_v5.md`: there is no longer any point at which a minor's
account exists, or their data is processed, ahead of parental consent.

**Account-linking is now an optional, parent-controlled feature, not an
exclusion.** A parent may optionally link a read-only bank view (via a
Stitch/Mono-style integration) to help verify a child's payment; honor-
system self-report remains the default path for parents who decline to
link. This reverses the prior `Clarifications_v10.md` exclusion decision,
whose NCR-avoidance rationale `ResearchFindings_v3.md` (Research House
Engagement 3) found likely mistaken. The underlying regulatory question —
whether the NCR or any other South African regulator actually reaches a
read-only, non-custodial account-verification service — remains
unresolved by desk research and gates this feature's ship date behind the
still-uncommissioned specialist legal opinion, consistent with the
existing v9 feature-level build-gating plan.

**Net effect this revision:** Critical Gap #3 (the pre-link carve-out) is
resolved by removal. The "foregone opportunity" reading of the
NCR-avoidance premise (`reviews/DevilsAdvocate.md`, v12 Objection 2) is
resolved by no longer forgoing the feature. Neither change resolves the
underlying, still-open legal questions (contractual capacity;
domestic-agreement presumption; ARB precedent absence; whether the NCR
regulates read-only linking) — both Critical Legal sections remain
**Partial**, and Confidence holds flat at **Medium**, bounded by these
unrelated untouched items, not by anything addressed this cycle. The
Readiness Score is unchanged at **52% (67/130)** — no Status moved this
revision, though a full Critical Gap closed (see "What Changed in v14").

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Objectives

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. `Clarifications_v14.md` Item 1 asked this Incubator
to check this section for carve-out-dependent language as part of the
ripple-effect review. **This Incubator's available inputs do not include
this section's full text** (v13 carries it forward only as an
"Unchanged from v12" pointer with no substantive content) — this
Incubator cannot confirm this section is clean of carve-out-dependent
language it has never read. Flagged as an input-scope limitation, not
certified as checked.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Same limitation as Stakeholders above:
`Clarifications_v14.md` Item 1 named this section for a ripple-effect
check this Incubator's available inputs cannot perform. Flagged, not
certified.

## Value Proposition

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Same limitation as Stakeholders above:
`Clarifications_v14.md` Item 1 specifically named this section (the
Executive Summary's platform/feature description was the other named
example, and that one has been directly addressed above since it is
visible in v13's text). This section's full text is not visible to this
Incubator beyond the v13 pointer. Flagged, not certified.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Base content unchanged from v13 (not visible to this Incubator beyond the
v13 pointer). **New this revision, per `Clarifications_v14.md` Item 2's
explicit instruction:** optional account-linking is added as a
trust/verification feature within the existing subscription model — it
does not introduce a new revenue line; its purpose is to give parents who
opt in an additional, automated way to verify a child's earnings claim,
alongside the existing honor-system self-report default. The feature is
gated behind the specialist legal opinion before it can ship (see Legal &
Compliance, Roadmap). Status remains Partial — this addition does not
resolve any of the business-model open items this Incubator does not
have visibility into from prior versions.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision. The unreconciled
subscriber-count discrepancy remains open (see Outstanding Questions).
See Financial Considerations below for the related family-vs-child
install-count ripple check.

## Operations

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Base content unchanged from v13 (not visible to this Incubator beyond the
v13 pointer). **Updated this revision on two points:**

**(1) Pre-link practice-data retention question — substantially narrowed,
not fully closed.** v13's open question ("what happens to a minor's
manually-entered practice data once a parent links and the feature
auto-populates with real earnings") depended on a scenario — an
independently-registered minor holding practice data before any parent
involvement — that no longer exists, since a minor cannot register at
all without a parent as custodian. **However, this Incubator flags a
residual ambiguity rather than declaring the question moot outright:**
it is not clear from `Clarifications_v14.md` whether "registration" (parent
as custodian) and a subsequent "budget/earnings-link" step remain two
distinct stages within the now fully parent-supervised flow — i.e.,
whether a parent-registered minor could still use a practice-only
budgeting tool before the parent formally sets up real budget/earnings
data. If such a stage still exists, a narrower version of the original
retention question could persist, now in a consented context. This is
added to Outstanding Questions rather than assumed resolved.

**(2) Optional account-linking — operational flow undocumented.** Per
`Clarifications_v14.md` Item 2, a parent may now opt in to linking a
read-only bank view. The operational mechanics of that opt-in (where in
the parent flow it is offered, what consent language is shown, how a
parent later un-links) are not specified in this cycle's inputs and are
added as a new open item. Confidence remains at **Medium**, not restored
to High — held flat, but for a different reason than v13's (the old
reason, undocumented pre-link retention handling, is substantially
narrowed; the new reason is the undocumented account-linking opt-in
flow).

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Base content unchanged from v13 (not visible to this Incubator beyond the
v13 pointer — flagged per the Stakeholders/Target Users limitation
above). **New this revision, per `Clarifications_v14.md` Item 2:**
optional read-only account-linking is added as a technology dependency
(a Stitch/Mono-style API integration), parent-opt-in only, gated behind
the specialist legal opinion before it ships. Honor-system self-report
remains the default technical path and requires no external integration.
No technology stack detail for the linking integration itself has been
specified in this cycle's inputs.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium (unchanged from v13) |
**Evidence:** Supported

**This section remains flagged Critical. Status is unchanged at
Partial.** The specialist legal opinion required to resolve the
section's remaining open items has still not been obtained.

**Pre-link independent-registration carve-out — RESOLVED this revision by
removal, not by legal confirmation.** `Clarifications_v14.md` Item 1
removes the feature that created this risk entirely: a minor can no
longer register, or have any data processed, without a parent acting as
registration custodian from the outset. This closes the specific
scenario `ResearchFindings_v3.md` substantiated as likely triggering
POPIA's Section 34/35 consent requirement at the point of registration —
that scenario can no longer occur. **This is a genuine, structural risk
elimination, not a Confidence-only evidentiary improvement** — it differs
in kind from v13's Low-to-Medium Confidence recovery, which was driven by
research quality, not by removing the underlying scenario. Per Playbook
Entry 4's distinction between confidence-in-assessment and
favorability-of-conclusion, this is worth stating precisely: this is a
favorability improvement (the risk itself is gone), not merely a clearer
picture of an unchanged risk. **This item is removed from the specialist
legal opinion's required scope** (see Validation Strategy, Outstanding
Questions). One residual ambiguity is flagged, not resolved: whether a
narrower, now-consented version of the practice-data question could
persist if a distinct post-registration, pre-budget-link stage still
exists (see Operations).

**Read-only account-linking — no longer an exclusion decision; now a
feature-level regulatory gate.** `Clarifications_v14.md` Item 2 makes
account-linking optional rather than excluded. The underlying regulatory
question `ResearchFindings_v3.md` addressed — whether the NCR's four
registration categories plausibly reach a read-only, non-custodial
account-verification service — **remains unresolved by desk research**;
Research House's Supported-tier, Medium-confidence finding (none of the
four categories plausibly fits) is an indication, not a legal conclusion,
and no NCR/FSCA/SARB document naming this exact service type was found.
What changes this revision is the **consequence** of that open question:
previously it justified a permanent product exclusion (and drove the
"foregone opportunity" risk reading in `reviews/DevilsAdvocate.md`, v12
Objection 2); now it gates a single shippable optional feature under the
existing v9 build-gating plan, and the honor-system default proceeds
regardless of how the question resolves. This item **remains** in the
specialist legal opinion's required scope.

**Minor contractual capacity, domestic-agreement presumption, ARB
precedent absence — untouched by this revision.** None of
`Clarifications_v14.md`'s two items addresses these. They remain exactly
as characterized in v13, pending specialist confirmation.

**Confidence holds flat at Medium, not because nothing changed, but
because the section's Confidence ceiling is set by these untouched
items, not by the item that was just resolved.** Per Playbook Entry 3,
this is stated explicitly so a flat Confidence tag is not misread as "no
progress" — Critical Gap #3 fully closed this cycle (see Critical Gaps
below), which a Confidence-only or Status-only view would not surface on
its own.

**Redesigned mechanic implications — unchanged from v13.** The
late-penalty mechanic being parent-incurred and parent-invisible-only
changes, but does not resolve, the terminology-to-minors risk: "invoice,"
"payslip," and "arrears" language is still applied in a product
explicitly directed at minors as young as 6.

The feature-level gating plan established in v9 (financial-trigger
features locked behind the opinion; foundational rails may proceed in
parallel) is unchanged and still applies. The pre-link
independent-registration carve-out's gate is removed along with the
feature it gated (there is nothing left to gate). The optional
account-linking feature is **added** to this gating plan as a new gated
item.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Base risk register unchanged from v13 (not visible to this Incubator
beyond the v13 pointer — the full risk list is understood to live in v12
or earlier). **Two items updated this revision:**

**Trust/enforcement risk — "foregone opportunity" framing RESOLVED;
regulatory-gate framing remains open.** v13 sharpened a risk that
MiniMoney was needlessly forgoing a feature (account-linking) that could
reduce enforcement risk, based on an NCR-avoidance premise
`ResearchFindings_v3.md` found likely mistaken. `Clarifications_v14.md`
Item 2 resolves this specific framing: the feature is no longer forgone.
**The risk is reframed, not eliminated:** it now reads as "the optional
account-linking feature cannot ship until the specialist legal opinion
clears the NCR question, and in the meantime the honor-system default
carries whatever enforcement-trust limitations it already had." This is
a narrower, better-defined risk than v13's, but it is still open.

**Pre-link independent-registration carve-out risk — RESOLVED by
removal.** The risk v13 sharpened (Supported-tier research indicating
registration itself likely triggers POPIA's consent requirement) applied
specifically to a feature that no longer exists. This item is closed and
moved to the resolved list (see Critical Gaps). The residual
post-registration-stage ambiguity flagged in Operations is **not**
treated as a continuation of this same risk at this time — it is a
distinct, smaller, open question, tracked separately in Outstanding
Questions.

The undocumented data-retention handling item is substantially narrowed
by the removal above (see Operations); the new undocumented
account-linking opt-in flow (also Operations) is added as a small new
open item under this section's general "undocumented technical/consent
mechanism" theme, not previously present in v13 in this form.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Base assumptions list unchanged from v13 (not visible to this Incubator
beyond the v13 pointer). **Two items updated this revision:**

**The v12/v13 assumption that "a narrow, single-feature, practice-data-
only pre-link carve-out sits in a materially lower-risk POPIA posture"
is now MOOT, not merely challenged.** The feature this assumption
described no longer exists. It is retained in the case record for
audit-trail continuity, marked **superseded by design change (v14)**
rather than "likely inaccurate, pending confirmation" (its v13
characterization) — the distinction matters because the assumption is no
longer a live input to any current product decision.

**The NCR-avoidance premise underlying the original Stitch/Mono exclusion
is decoupled from the current product decision, not resolved.** The
premise itself (does the NCR reach read-only account-linking) remains
exactly as unconfirmed as it was in v13 — `Clarifications_v14.md` does
not resolve it, it only changes what depends on it. Previously the
premise's accuracy was the sole basis for a permanent exclusion decision;
now the feature ships or doesn't ship based on the specialist opinion's
eventual answer, regardless of which way that answer falls. This is a
more defensible position (the product decision no longer rests entirely
on an unconfirmed assumption) but the assumption itself is unchanged in
evidentiary status — still Supported-tier-questioned, not specialist-
confirmed.

The contractual-capacity research-claim assumption from v13 is unchanged
by this revision — not addressed by `Clarifications_v14.md`.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Base roadmap unchanged from v13 (not visible to this Incubator beyond the
v13 pointer). **Updated this revision:** the pre-link carve-out's
build-gate is removed (nothing left to gate). The optional
account-linking feature is **added** to the v9 feature-level gating plan
as a new gated item, to be built only after the specialist legal opinion
clears the NCR question — honor-system self-report proceeds at launch
regardless. The specialist legal opinion's commissioning trigger remains
"event-based, once a stable working model exists," a point
`reviews/DevilsAdvocate.md` (v12, Objection 4) questioned directly; this
revision's changes do not alter that trigger, and — per v13's own
repeated observation — the opinion's required scope has now been
sharpened or narrowed across four consecutive revisions (v10, v11, v12,
v13, and now v14) without being commissioned. This Incubator repeats,
without prescribing a decision, that the event-based trigger may warrant
reconsideration as a dated one.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. **Ripple-effect check performed per
`Clarifications_v14.md` Item 1's explicit prompt regarding the
family-vs-child install-count ambiguity — checked, not resolved.** It is
plausible the carve-out was a contributing factor (an
independently-registered minor account, prior to this revision, could
have existed and been counted separately from a "family" install); it is
equally plausible the ambiguity is entirely attributable to the
up-to-4-children-per-family subscription structure (Executive Summary),
unrelated to the carve-out. This Incubator's inputs this cycle do not
include the original computation detail behind the 180-1,830 vs.
360-2,440 figures, so this cannot be resolved either way from what is
available. Flagged explicitly as an input-scope limitation rather than
claimed as resolved by the carve-out's removal. The unreconciled
subscriber-count discrepancy itself remains open (see Outstanding
Questions).

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

1. **Legal validation** — required scope is narrower this revision (the
   pre-link carve-out's POPIA posture is removed from what the specialist
   opinion must cover, since the feature no longer exists), but the
   opinion itself remains unobtained. See Roadmap's repeated observation
   on the "event-based" trigger.
2. **Primary user-research validation** — unchanged from v13.
3. **Child-development/age-appropriateness review** — unchanged from
   v13.
4. **Trust/enforcement and dispute-mechanism validation** — unchanged in
   substance, with one addition: this must now also validate whether
   parents actually opt into account-linking when offered, and whether
   doing so measurably improves trust/enforcement outcomes relative to
   honor-system self-report alone — an empirical question this cycle's
   design change introduces and does not answer.
5. **Market/demand validation** — unchanged from v13.
6. **Pricing/conversion validation** — unchanged from v13.
7. **Curriculum validation** — unchanged from v13.
8. **Pre-link carve-out compliance validation — RESOLVED by removal.**
   The feature this validation item existed to test no longer exists.
   Retained here for audit-trail continuity only, per the precedent
   already set for other resolved items in this case (Critical Gaps #7,
   #8).
9. **Account-linking feature validation (new this revision)** — before
   the optional account-linking feature ships, it requires both (a)
   specialist legal confirmation that the NCR (or no regulator) reaches
   this service, and (b) the opt-in consent flow and parent-facing
   language to be designed and reviewed, neither of which exists yet
   (see Operations, Technology).

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in content and treatment from v13, with one addition:
`Clarifications_v14.md` is added as new supporting evidence, documented
at **Verified**-tier — this is direct user confirmation of a product
design decision, not vendor research or Incubator inference, and is the
highest evidentiary tier this case uses. It is Verified as to *what the
design now is* (carve-out removed; linking optional); it is explicitly
**not** Verified as to the underlying legal questions the design change
does not resolve (NCR scope; contractual capacity; domestic-agreement
presumption; ARB precedent), which remain at their prior, lower
evidentiary tiers pending the specialist opinion.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this revision (retained for audit-trail continuity):**

- Does independent minor account registration — before any parent link
  exists — itself constitute processing of a minor's personal
  information under POPIA? **RESOLVED by design change, not by legal
  answer**: `Clarifications_v14.md` Item 1 removes independent
  registration entirely, so this scenario can no longer occur. The
  general statutory question `ResearchFindings_v3.md` researched (does
  POPIA's "processing" definition attach at registration) remains valid
  research but no longer applies to any live MiniMoney feature.
- Given `ResearchFindings_v3.md`'s finding that the NCR-avoidance premise
  may be mistaken, does the user wish to revisit the account-linking
  exclusion? **RESOLVED**: `Clarifications_v14.md` Item 2 — yes, the
  feature is now optional rather than excluded.

**Still open, sharpened this revision:**

- Does the specialist legal opinion confirm or refute that read-only
  account-linking (Stitch/Mono) triggers NCR payment-facilitation
  obligations? Now specifically gates the optional account-linking
  feature's ship date (v9 gating plan), rather than justifying a
  permanent exclusion. (Legal & Compliance, Risks, Roadmap)

**New this revision:**

- Does a distinct "budget/earnings-link" step still exist after
  parent-custodian registration, within which a practice-only budgeting
  tool might still be accessible before real earnings data is
  configured? If so, does that narrower, now-consented scenario still
  raise any residual practice-data-as-personal-information question?
  (Operations, Legal & Compliance)
- What is the operational and UX flow for a parent opting into
  account-linking (where offered, what consent language, how to
  un-link)? (Operations, Technology, Validation Strategy)
- Does the family-vs-child install-count ambiguity trace in any part to
  the now-removed carve-out, or is it entirely attributable to the
  up-to-4-children-per-family subscription structure? This Incubator's
  inputs this cycle cannot resolve this and flag it as an open
  reconciliation item rather than assuming either answer. (Financial
  Considerations, Revenue & Costs)

**Still open, carried forward unchanged from v13:** whether the user
wants to revisit the "event-based, once a stable working model exists"
specialist-opinion commissioning trigger in favor of a dated one, now
that four consecutive revisions have narrowed or sharpened its scope
without commissioning it; the family-vs-child install ambiguity; the
unreconciled subscriber-count discrepancy (180-1,830 computed vs.
360-2,440 cited); the recommended preliminary legal read's adoption
decision; fund custody mechanics; task verification; dispute-escalation
beyond 48 hours; payment-routing timeline; late-penalty cap rationale;
Fintech Advance scope; exam-bonus data source; Mbucks-peg flexibility;
curriculum age-band splits; app-store policy sub-questions; MoneyAfrica
Kids' unpublished premium price; whether informal engineering-cost
quotes will be sought; the external-help budget ceiling; the
schools-partnership channel's timeline/target school count/resourcing
plan; the domestic-agreement presumption's application to MiniMoney's
"agreed condition of budget setup" framing.

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

Points earned: **67** (unchanged from v13 — no Status changed this
revision, despite a full Critical Gap closing; see "What Changed in v14"
and Playbook Entry 1/3 notes above).

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130** (unchanged).

**Readiness Score = 67 / 130 = 51.5%, rounded to 52%. Unchanged from
v13.**

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
52% (v13) → **52% (v14).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB/contract-law legal opinion remains
   unobtained. Its required scope is **narrower this revision** (the
   pre-link carve-out's POPIA posture is removed — see Gap #3, RESOLVED)
   but still covers: domestic-agreement presumption; minor contractual
   capacity for the payslip obligation; the user's own unconfirmed claim
   that no law bars the parent-child contractual structure; the
   NCR-avoidance premise, now specifically gating the optional
   account-linking feature rather than justifying a permanent exclusion.
   Confidence holds flat at Medium — bounded by these untouched items,
   not by anything addressed this cycle.

2. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions)** — unresolved. Checked this revision
   per `Clarifications_v14.md` Item 1's prompt for a possible connection
   to the now-removed carve-out; this Incubator's inputs cannot confirm
   or rule out that connection. Carried forward as an open
   reconciliation item.

3. **Pre-link independent-registration carve-out — RESOLVED in v14 by
   removal.** `Clarifications_v14.md` Item 1 removes the feature
   entirely; a minor can no longer register without a parent as
   custodian. Retained here for audit-trail continuity only, consistent
   with the treatment already given to Gaps #7 and #8.

4. **Account-linking regulatory gate (formerly "late-penalty enforcement
   mechanism / NCR-avoidance premise")** — reframed this revision. The
   "foregone opportunity" framing is resolved: account-linking is no
   longer excluded, it is optional. The underlying regulatory question
   (does the NCR reach a read-only, non-custodial service) remains
   unresolved by desk research and now specifically gates the optional
   feature's ship date, per the existing v9 build-gating plan. The
   honor-system self-report default is unaffected and proceeds at
   launch regardless of this question's eventual answer.

5. **Child-development/age-appropriateness risk (Success Criteria,
   Risks, Validation Strategy)** — unchanged from v13; not addressed by
   this revision.

6. **Subscriber-count discrepancy (Revenue & Costs)** — unresolved,
   carried forward unchanged from v13.

7. **Request-for-payment feature inconsistency — RESOLVED in v11**,
   retained here for audit-trail continuity only.

8. **90-day vs. annual funnel tension — RESOLVED in v10**, retained here
   for audit-trail continuity only.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v13. Not addressed this revision.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium (unchanged from v13) |
**Evidence:** Supported

**This section's central open question is resolved as a live scenario
this revision, though Status and Confidence hold flat.** Since a minor
can no longer register, or have any data processed, without a parent
acting as custodian from the outset, the question that drove v12's
downgrade and v13's partial recovery — does independent registration
itself trigger POPIA's Section 34/35 consent requirement — **can no
longer arise in MiniMoney's actual design.** `ResearchFindings_v3.md`'s
statutory research (POPIA's broad "processing" definition; Section 34's
unqualified prohibition) remains valid, sourced research, but no longer
applies to any live feature.

**Confidence is held at Medium, not raised to High, for reasons unrelated
to the resolved question.** This section's Status has been Partial since
v9-v13 for several independent reasons, none of which this revision
touches: the technical mechanism for the (now-universal, no-exception)
consent gate is still undocumented; the two explicit user
risk-accepted assumptions (POPIA Section 14 retention sufficiency;
exam-bonus mechanic's no-schools-data-privacy-dimension assumption)
remain accepted but unreviewed by a specialist; Google Play's Families
Policy loyalty-point disclosure requirement and Apple's Kids Category
IAP-currency question remain open; the confirmed absence of ARB/NCR
precedent for "payslip"/"invoice"/"late penalty" terminology applied to
minors is unchanged. Per Playbook Entry 3, this flat Confidence is
stated explicitly as deliberate, not an oversight: the item that
improved (registration-trigger risk) was never the sole reason this
section held at Medium rather than High, so its resolution alone does
not move the tag.

**Residual item, new this revision:** whether a distinct
post-registration, pre-budget-link stage still exists within the now
fully parent-supervised flow, and if so, whether a narrower version of
the practice-data-as-personal-information question persists within it
(see Operations, Outstanding Questions). This is not assumed resolved by
the carve-out's removal.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 52% (67/130),
  unchanged from v13. Progression: 24% (v3) → 36% (v4) → 39% (v5) → 40%
  (v6) → 40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52%
  (v12) → 52% (v13) → **52% (v14).**

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
is unchanged at 52% — this revision resolves Critical Gap #3 outright
(feature removed) and substantively reframes Gap #4 (no longer a
foregone-opportunity risk), but because the Status-based rubric does not
directly credit gap-count reduction, and because the remaining untouched
items in both Critical sections (contractual capacity, domestic-agreement
presumption, ARB precedent absence, the NCR question for the now-optional
linking feature) keep Status at Partial, the score does not move. This is
stated explicitly, consistent with Playbook Entry 1, so the unchanged
score is not misread as this revision having made no progress. A v15
would need: (a) the actual specialist legal opinion obtained, now with a
narrower required scope than at any prior version; (b) resolution of the
family-vs-child install-count ambiguity; (c) resolution of the
subscriber-count discrepancy; (d) clarification of whether a
post-registration, pre-budget-link stage still exists (new this
revision); (e) the account-linking opt-in operational flow documented;
and (f) the required child-development review conducted, to meaningfully
advance the Readiness Score further.
