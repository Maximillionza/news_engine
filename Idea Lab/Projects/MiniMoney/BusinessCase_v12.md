# Business Case: MiniMoney — v12

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v11.md` (prior version), and
> `Clarifications_v12.md` (user responses to three items — minor
> contractual capacity, closure of read-only account-linking as a present-
> scope NCR-driven decision, and a narrow pre-parent-link independent-
> registration carve-out — 2026-07-09). This document is self-certified
> against the Incubator completion gate. Sections not touched by
> `Clarifications_v12.md` are carried forward as "Unchanged from v11" —
> consistent with how v11 itself carried forward untouched v10 content —
> since this Incubator's authorized inputs for this cycle are limited to
> `00_CaseStudy.md`, `BusinessCase_v11.md`, and `Clarifications_v12.md`
> only; no other prior version was read or used as a source.

> **Changes from v11 — summary of what this revision addresses:**
> `Clarifications_v12.md` resolves or sharpens three items, all within
> Legal & Compliance's orbit.
>
> **(1) Minor contractual capacity.** The user states the structural
> design directly: the payment obligation runs against the parent, not
> the child; the child is a participant, not a bound party; a task's
> completion is the condition of remuneration, not a legal obligation
> the child can be compelled to perform. This structural framing is
> documented as a **Verified**-tier design statement — the user is
> describing their own intended design, which they are authoritative on.
> Separately, the user offers a legal claim — "based on my research,
> there is no law or act that prevents contracts between a minor and a
> parent" — which is explicitly **not** treated as a settled legal
> conclusion, per the Chief of Staff's instruction. It is documented as
> an **Assumed**-tier, user-supplied research finding requiring
> specialist confirmation, on exactly the same footing as every other
> open legal question in this case, not as a fact that closes the
> question.
>
> **(2) Read-only account-linking (Stitch/Mono) — closed as a deliberate
> present-scope decision, not a deferral.** The user confirms staying
> with the honor-system model is driven by a wish to avoid triggering NCR
> payment-facilitation requirements, not by cost, vendor immaturity, or
> timing — reframing what Research House Engagement 2 and v11 had
> characterized as a "later-stage/V2+ feature" into a present, deliberate
> non-adoption. This closes two of v11's Outstanding Questions (the
> Stitch/Mono sales-inquiry question; the "is the user comfortable
> formally adopting honor-system-only" question) but, per Devil's
> Advocate scrutiny below, introduces a new, symmetrical open question:
> the user's own premise (that account-linking would trigger NCR
> obligations) is itself an unconfirmed regulatory interpretation, not a
> specialist-confirmed one.
>
> **(3) A narrow pre-parent-link independent-registration carve-out.** A
> minor may now download, install, and register an account independently
> of any parent link, and — before any parent link exists — access
> exactly one feature: a "budgeting" tool in which the minor manually
> enters practice/hypothetical income data. Once a parent account links,
> the same feature auto-populates with the minor's real Mbuck earnings.
> Per explicit Chief of Staff instruction, this is treated with the same
> directional compliance rigor applied to the education-only direct-
> signup carve-out this case closed in v5 by collapsing all access behind
> a universal parental-consent gate — it is **not** assumed compliant
> merely because it is narrower in feature scope than the carve-out
> previously closed. This is characterized below as a live, unresolved
> POPIA risk requiring specialist confirmation, and as a direct
> qualification of the "a minor cannot access any part of the app without
> a pre-existing, consenting parent account" claim stated in v11's
> Executive Summary, which is corrected below rather than left standing
> alongside a contradicting fact.

## What Changed in v12 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

1. **Legal & Compliance — minor contractual capacity sub-question
   updated, not resolved.** The structural design (obligation runs
   against the parent, not the child) is now documented as a Verified
   design fact. The user's supporting legal claim ("no law or act
   prevents this") is documented as an Assumed-tier, unconfirmed research
   finding — it sharpens what the specialist opinion must confirm or
   correct, exactly as Research House Engagement 2's contract-law desk
   research did in v11, but does not itself resolve the question.

2. **Operations / Roadmap / Technology / Outstanding Questions — read-
   only account-linking exclusion reframed as a deliberate, NCR-driven
   present-scope decision.** This closes two v11 Outstanding Questions.
   A new, narrower open question replaces them: whether the user's stated
   NCR-avoidance premise is itself legally accurate — flagged for the
   specialist opinion rather than accepted at face value, applying the
   same scrutiny standard used for every other legal claim in this case.

3. **Operations, Legal & Compliance, Legal & Compliance — Child Data &
   Consent, Risks, Assumptions, Executive Summary — pre-link independent-
   registration carve-out documented as a new, unresolved compliance
   question, not a resolved feature.** The carve-out is described fully
   in Operations. The Executive Summary's prior "zero pre-link access"
   claim is corrected to reflect the narrow exception rather than left
   standing in contradiction with it (per standing instruction to check
   for and close ripple effects before marking a section clean). The
   POPIA Section 34/35 question this reopens — whether independent minor
   account registration and practice-data entry, even absent real money
   or real earnings data, constitutes processing of a minor's personal
   information requiring prior competent-person consent — is
   characterized as a live, unresolved risk and added to the specialist
   legal opinion's required scope. It is explicitly **not** resolved as
   safe by inference from its narrower scope.

**Net effect on Readiness Score: none.** No section's Status changes
this revision. Per the playbook principle that analytical fixes (naming
a claim's evidentiary tier precisely, correcting an internal
contradiction, sharpening a specialist opinion's required scope) do not
automatically move a Readiness Score built on Status alone, this
revision's substantial rigor is not reflected in the score, and that is
stated explicitly here rather than left for a later reviewer to
misinterpret an unchanged score as the clarifications having been
ignored. Two Critical sections (Legal & Compliance; Legal & Compliance —
Child Data & Consent) have their Confidence lowered from Medium to Low,
reflecting that this is now the third consecutive revision to add
required scope to the still-uncommissioned specialist opinion without
resolving any of it, and that this revision specifically reopens a
question (pre-link minor access without consent) the case previously
believed fully closed. Confidence changes do not affect the Readiness
Score under this rubric, only Status does — this is also stated
explicitly rather than left implicit. **Readiness Score: 67/130 = 51.5%,
rounded to 52%, unchanged from v11.**

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
child has zero visibility into it. **Corrected this revision:** a minor
cannot access any *substantive* part of the app — task assignment,
earnings, payslip, invoice, or store — without a pre-existing, consenting
parent account; however, a minor **may** independently download, install,
and register an account, and before any parent link exists, that account
can access exactly one feature (a "budgeting" tool for manually-entered
practice income) — a narrow exception to the otherwise-universal consent
gate, not an absolute rule as prior versions stated.

**This revision resolves, sharpens, or reopens three Legal & Compliance
items, moving no section's Status.** The design structure behind the
contractual-capacity question is now stated plainly (the obligation runs
against the parent, not the child) as a Verified design fact, but the
user's own supporting legal-research claim ("no law bars this") is
explicitly held at Assumed-tier pending specialist confirmation, not
accepted as settled. The decision to exclude read-only account-linking
(Stitch, Mono) is reframed from a later-stage deferral into a deliberate,
present-scope decision driven by a wish to avoid triggering NCR payment-
facilitation obligations — itself an unconfirmed regulatory premise, now
flagged for the same specialist scrutiny. Most significantly, a narrow
pre-parent-link carve-out — independent minor registration plus access to
a single practice-only budgeting feature — is documented as a live,
**unresolved** POPIA risk, applying the same rigor this case applied when
it closed a broader version of the same question in v5 (education-only
direct signup, dropped in favor of a universal consent gate). This
carve-out is not assumed compliant merely because its feature scope is
narrower; it is flagged for the specialist legal opinion like every other
open compliance question in this case. The Readiness Score is unchanged
at **52% (67/130)** — this revision adds rigor and corrects an internal
contradiction but resolves no Status-moving gap, and both Critical Legal
sections have their Confidence lowered to Low to reflect compounding,
still-uncommissioned legal exposure.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed by `Clarifications_v12.md`.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Objectives

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. **One addition:** the pre-link independent-
registration carve-out (see Operations) creates a new, minor-only user
path into the product (a minor with no linked parent, using only the
practice-budgeting feature) that did not previously exist in any
described version of this case. This is noted here as a new user-type
distinction — it does not change this section's Status, which remains
Partial for reasons independent of this addition, but should be reflected
in any future user-research or persona work.

## Value Proposition

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision. The
unreconciled subscriber-count discrepancy remains open (see Outstanding
Questions).

## Operations

**Status:** Complete | **Confidence:** Medium (down from High) |
**Evidence:** Supported

**Read-only account-linking exclusion — reframed, not newly decided.**
Per `Clarifications_v12.md` Item 2, continuing the honor-system self-
report model (rather than integrating Stitch or Mono) is confirmed as a
deliberate, present-scope design decision driven by a wish to avoid
triggering NCR payment-facilitation requirements — not, as v11's
Research House-informed framing had it, a resource/timing-driven
deferral to a later stage. The user notes this "may change with further
development" but this is not a stated plan for any near-term version.
This does not change Operations' Status or the underlying mechanic — it
sharpens the *reason* for a decision already reflected in the case — but
it is noted here because it closes two Outstanding Questions (see below)
and because Devil's Advocate scrutiny (see `reviews/DevilsAdvocate.md`)
flags the NCR-avoidance premise itself as unconfirmed, symmetric to the
contractual-capacity claim.

**New feature — pre-parent-link independent registration with a single
practice-budgeting feature.** Per `Clarifications_v12.md` Item 3, the
mechanic is now: a minor may download, install, and register an account
independently of any parent. Before a parent account is linked (via the
parent's email or Google account), the minor's account can access
exactly one feature — a "budgeting" tool in which the minor manually
captures practice/hypothetical income data. Once a parent links their
account, this same feature auto-populates with the minor's real Mbuck
earnings rather than manual entry. No other feature (tasks, payslip,
invoice, store, exam bonus) is accessible pre-link. The user has stated
any future expansion of pre-link functionality will be evaluated for
compliance impact individually, not as a blanket policy relaxation.

**Status assessment.** This mechanic is described coherently and without
internal self-contradiction — the bar this Status tracks, per the
precedent set in v11 for Operations. However, per the standing instruction
to check for ripple effects before marking a section Complete again: this
new mechanic directly contradicted the "a minor cannot access any part of
the app without a pre-existing, consenting parent account" claim carried
in v11's Executive Summary. That claim has been corrected in this
revision (see Executive Summary above) rather than left standing
alongside a fact that contradicts it — the ripple effect is resolved, not
merely named. Status remains Complete on that basis.

**Confidence lowered to Medium, however, for a genuine specification
gap this new feature introduces.** The clarification does not state what
happens to a minor's manually-entered practice data once a parent links
and the feature auto-populates with real earnings — is practice data
discarded, retained alongside real data, or silently overwritten? This is
not merely a UX nicety; it has a direct POPIA Section 14
(retention/minimisation) dimension for pre-link data specifically, since
that data was captured before any parental consent existed. This is
named as a new Outstanding Question, not assumed away, and not treated as
blocking Complete status for the same reasons the "no recourse mechanism"
gap did not block Operations' Complete status in v11 — it is a scope/
specification gap, not a contradiction.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11 in its core gaps. **One refinement this revision:**
the read-only account-linking question (Stitch, Mono) is no longer an
open technology-stack-planning item for the near term — per Operations
above, it is now excluded by deliberate present-scope decision, not
merely deprioritized. This removes one item from Technology's implicit
backlog but does not change this section's Status, which remains Partial
for reasons predating and independent of this item (core platform/
architecture technology-stack decisions remain undocumented in this
case).

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Low (down from Medium) |
**Evidence:** Supported

**This section remains flagged Critical, and its Status is unchanged.**
The underlying legal uncertainty — money-transmitter characterization of
the invoice/payment trigger; the absence of ARB/NCR precedent for
"payslip"/"invoice"/"late penalty" terminology applied to minors; POPIA
Section 34/14 sufficiency — is unresolved, and the specialist legal
opinion required to address it has still not been obtained. Confidence
is lowered to Low this revision: this is the third consecutive revision
(v10, v11, v12) to add required scope to that still-uncommissioned
opinion without resolving any prior item, and this revision specifically
reopens a question (see Legal & Compliance — Child Data & Consent below)
the case previously treated as closed.

**Minor contractual capacity — updated, not resolved.** Per
`Clarifications_v12.md` Item 1, the structural design is now stated
directly and documented as a **Verified** design fact: the payment
obligation runs against the parent, not the child; the child is described
as a participant in a task-for-remuneration arrangement, not a bound
party to an enforceable contract; incomplete tasks simply forfeit that
task's remuneration rather than triggering any obligation the child could
be compelled to perform. This is a coherent design statement and is
documented as such. Separately, the user's claim that "there is no law or
act that prevents contracts between a minor and a parent" and that
MiniMoney "does not fall into any of those [restricted] categories" is
**not** treated as a settled legal conclusion — per direct instruction,
this is an unconfirmed, user-supplied research finding, documented at
**Assumed**-tier, and added to what the specialist opinion must confirm
or correct, on the same footing as v11's domestic-agreement-presumption
and minor-contractual-capacity-for-the-payslip-obligation questions,
neither of which this clarification resolves. The design framing itself
(task completion as a condition of remuneration, not a binding promise to
the child) may be relevant to how a specialist assesses the domestic-
agreement presumption, but the Incubator does not attempt that legal
analysis itself.

**Read-only account-linking exclusion — new premise flagged for
scrutiny.** Per `Clarifications_v12.md` Item 2, the user's rationale for
excluding Stitch/Mono is that pursuing it would trigger National Credit
Regulator payment-facilitation requirements. This rationale is not itself
confirmed by any specialist opinion, Research House finding, or cited
source — it is the user's own regulatory interpretation, symmetric in
evidentiary status to the contractual-capacity claim above. It is
documented at **Assumed**-tier and added as a new item the specialist
opinion should address: whether read-only, non-payment-initiating
account-linking would in fact trigger NCR payment-facilitation
obligations, or whether this premise is itself over-cautious. This
matters because MiniMoney may be excluding a feature that could otherwise
strengthen the honor-system enforcement question (see Risks) based on an
unverified legal premise.

**Pre-link independent-registration carve-out — new, unresolved POPIA
risk, characterized with the same rigor as the v5 carve-out closure.**
Per `Clarifications_v12.md` Item 3 and direct Chief of Staff instruction,
this is not resolved as safe by inference from its narrower scope. The
directional assessment: POPIA Sections 34-35 require prior consent from a
competent person (a parent or guardian) before processing a child's
personal information, subject to limited exceptions (e.g., information
made public by the child themselves, or otherwise permitted by law) that
do not appear applicable here. Independent minor account registration —
before any parent link exists — necessarily involves collecting some
personal information about the minor (at minimum, whatever identifying
data the registration flow requires, e.g. name, age/date of birth,
possibly an email address) in order to create the account at all. This
appears to constitute processing of a minor's personal information
**at the point of registration itself**, independent of what the minor
subsequently does inside the app — meaning the practice-only, no-real-
money nature of the budgeting feature may not be the operative fact for
this specific question. Separately, even the practice/hypothetical
income data entered into the budgeting feature, while not reflecting the
minor's real circumstances, is still information tied to an identified
minor's account and may itself constitute the minor's personal
information under POPIA's broad definition, regardless of whether it is
"real" in a financial sense. Both of these are **directional concerns,
not legal conclusions** — the Incubator is not a law firm and does not
resolve POPIA questions definitively. This is characterized here with the
same rigor this case applied when it closed the broader education-only
direct-signup carve-out in v5, precisely because the carve-out is
narrower this time, not because narrower scope has been shown to change
the legal analysis. This is added as a required item for the specialist
legal opinion and is separately documented in Legal & Compliance — Child
Data & Consent below.

**Redesigned mechanic implications — unchanged from v11.** The
late-penalty mechanic being parent-incurred and parent-invisible-only
changes, but does not resolve, the terminology-to-minors risk: "invoice,"
"payslip," and "arrears" language is still applied in a product
explicitly directed at minors as young as 6.

The feature-level gating plan established in v9 (financial-trigger
features locked behind the opinion; foundational rails may proceed in
parallel) is unchanged and still applies. The pre-link independent-
registration carve-out is now explicitly added to that same gate: it
should not proceed to build or pilot ahead of the specialist opinion's
view on the POPIA question above, notwithstanding that it is currently
described as a "final design" decision by the user.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Carried forward from v11, with three updates:

**Trust/enforcement risk — narrowed premise now itself flagged as
unconfirmed.** v11 treated the exclusion of read-only account-linking as
a resource/timing-driven deferral, informed by category-consistency
evidence. This revision reveals the actual driver is a deliberate,
NCR-avoidance-motivated decision (`Clarifications_v12.md` Item 2) — but
that motivating premise is itself unconfirmed (see Legal & Compliance).
This adds a new dimension to the existing trust/enforcement risk: the
case may be foreclosing a feature that could reduce enforcement risk,
based on an unverified regulatory assumption, rather than a confirmed
one. Risk is retained and its framing sharpened, not resolved.

**New — pre-link independent-registration carve-out reopens a
previously-closed compliance risk pathway.** This case closed a broader
version of this exact risk in v5 (dropping the education-only direct-
signup carve-out for a universal consent gate) specifically because of
POPIA exposure. The new narrow carve-out (Operations; Legal & Compliance)
reintroduces a version of that same risk pathway, and the Incubator has
not found, and was instructed not to assume, that narrower feature scope
resolves it. This is added as a new risk item: MiniMoney may be exposed
to the same category of compliance risk it previously eliminated by
design, via a decision made without specialist legal review.

**New — undocumented data-retention handling for pre-link practice
data.** See Operations. Whether manually-entered practice income data is
discarded, retained, or overwritten upon parent-link is undocumented,
creating a secondary, narrower POPIA Section 14 (retention/minimisation)
question layered on top of the consent question above.

Both new items are added to what the required child-data-and-consent
specialist review (see Validation Strategy) must address, alongside the
existing legal opinion.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11, with two additions:

**New this revision — it is assumed, pending specialist confirmation,
that the user's contractual-capacity research finding ("no law or act
prevents" the parent-child task-for-remuneration structure) accurately
reflects South African law.** This is explicitly named as an assumption,
not a fact, per direct instruction — the Incubator does not adopt the
user's legal research as its own conclusion.

**New this revision — it is assumed, pending specialist confirmation,
that a narrow, single-feature, practice-data-only pre-link carve-out
sits in a materially lower-risk POPIA posture than the broader
education-only carve-out this case closed in v5.** This assumption is
explicitly **not** confirmed and is under active scrutiny in this
revision (see Legal & Compliance) — it is documented as an assumption
precisely because the Incubator was instructed not to resolve it as
safe by inference, and the case should not proceed as though this
assumption already holds.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in overall structure from v11. **One refinement this
revision:** read-only account-linking (Stitch, Mono) is no longer framed
as a later-stage/V2+ feature under active future consideration — per
`Clarifications_v12.md` Item 2, it is a deliberate present-scope
exclusion, revisitable only if the underlying NCR-avoidance premise
changes with further app development (not a scheduled or committed
roadmap item). This sharpens, but does not resolve, Roadmap's Partial
status: no dated milestone plan, phased budget, or external-help budget
ceiling has been supplied, and "stable working model" remains a judgment
call, not a checkable milestone. **Also added:** the pre-link
independent-registration carve-out is explicitly gated behind the
specialist legal opinion (see Legal & Compliance) and should not be
built or piloted ahead of that opinion's view.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not directly addressed this revision. The
family-vs-child install-count ambiguity and the unreconciled subscriber-
count discrepancy remain open (see Outstanding Questions).

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

1. **Legal validation** — unchanged in mechanism from v11; the
   specialist opinion's required scope is sharpened for a third
   consecutive revision (minor contractual capacity claim; NCR-avoidance
   premise for account-linking exclusion; pre-link carve-out's POPIA
   posture), but the opinion itself remains unobtained. Given the
   pattern of repeated scope-sharpening without commissioning, the
   Incubator flags — without prescribing a decision — that the "event-
   based, once a stable working model exists" trigger may warrant
   reconsideration as a dated trigger instead, since the model's scope
   keeps expanding before that event is ever reached.
2. **Primary user-research validation** — unchanged from v11.
3. **Child-development/age-appropriateness review** — unchanged from
   v11; the pre-link carve-out is a data-privacy/consent question, not a
   child-development one, and is not added to this review's scope.
4. **Trust/enforcement and dispute-mechanism validation** — updated
   this revision: the honor-system-only approach is now understood as a
   deliberate NCR-avoidance decision rather than a resource-driven
   deferral, but this reclassification does not substitute for empirical
   pilot validation of whether parents and children find the model
   trustworthy in practice, nor does it resolve whether the NCR-avoidance
   premise itself is accurate (see Legal & Compliance).
5. **Market/demand validation** — unchanged from v11.
6. **Pricing/conversion validation** — unchanged from v11.
7. **Curriculum validation** — unchanged from v11.
8. **New — pre-link carve-out compliance validation.** Required before
   the pre-link independent-registration feature proceeds to build or
   pilot: specialist confirmation of whether independent minor account
   registration and practice-data entry, absent any parent link,
   requires prior competent-person consent under POPIA. This is folded
   into the same specialist legal opinion as Item 1 above, not treated
   as a separate engagement, since both route to the same unresolved
   dependency.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in content and treatment from v11, with one addition: the
user's own contractual-capacity research claim (`Clarifications_v12.md`
Item 1) is added as new evidence, but documented at **Assumed**-tier, not
Supported or Verified — it is the user's characterization of external
law, not a confirmed design fact about their own product, and per
standing instruction is not treated as authoritative merely because the
user is confident in it.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Resolved this revision (removed from the open list):**
- Whether the user wants a direct sales inquiry made to Stitch and/or
  Mono, or whether this is deferred — resolved: neither; account-linking
  is a deliberate present-scope exclusion, not a pending vendor decision.
- Whether the user is comfortable formally adopting "honor-system only
  at launch, account-linking deferred to V2+" — resolved and reframed:
  it is not "deferred to V2+" but presently and deliberately excluded for
  NCR-avoidance reasons, revisitable only if that reasoning changes.

**New this revision:**

- Does the specialist legal opinion confirm or refute the user's claim
  that no South African law restricts a parent-child task-for-
  remuneration arrangement of this kind? (Legal & Compliance)
- Does the specialist legal opinion confirm or refute the user's premise
  that read-only account-linking (Stitch/Mono) would trigger NCR
  payment-facilitation obligations — or is MiniMoney excluding a
  potentially compliant, risk-reducing feature based on an unverified
  legal assumption? (Legal & Compliance, Risks)
- Does independent minor account registration — before any parent link
  exists — itself constitute processing of a minor's personal
  information under POPIA, requiring prior competent-person consent,
  regardless of what feature the minor subsequently accesses? (Legal &
  Compliance, Legal & Compliance — Child Data & Consent)
- Does manually-entered practice income data in the pre-link budgeting
  feature constitute the minor's personal information under POPIA, even
  though it is hypothetical and does not reflect real earnings? (Legal &
  Compliance — Child Data & Consent)
- What happens to a minor's manually-entered practice data once a parent
  account links and the feature auto-populates with real earnings — is
  it discarded, retained, or overwritten? (Operations, Legal & Compliance
  — Child Data & Consent, POPIA Section 14)
- With the specialist legal opinion now carrying a scope that has grown
  across three consecutive revisions without being commissioned, does
  the user want to revisit the "event-based, once a stable working model
  exists" trigger in favor of a dated commissioning trigger? (Validation
  Strategy)

**Still open, carried forward unchanged from v11:** with the request-for-
payment feature removed (v11), the case still describes no in-app
mechanism for a child or parent to flag an overdue base-wage payslip
payment; the family-vs-child install ambiguity; the unreconciled
subscriber-count discrepancy (180-1,830 computed vs. 360-2,440 cited);
the recommended preliminary legal read's adoption decision; fund custody
mechanics; consent-gate technical mechanism; task verification; dispute-
escalation beyond 48 hours; payment-routing timeline; late-penalty cap
rationale; Fintech Advance scope; exam-bonus data source; Mbucks-peg
flexibility; curriculum age-band splits; app-store policy sub-questions;
MoneyAfrica Kids' unpublished premium price; whether informal engineering-
cost quotes will be sought; the external-help budget ceiling; the
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

Points earned: **67** (unchanged from v11 — no Status changed this
revision).

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130** (unchanged).

**Readiness Score = 67 / 130 = 51.5%, rounded to 52%. Unchanged from
v11.**

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → **52% (v12).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB/contract-law legal opinion remains
   unobtained. Its required scope has now been sharpened across three
   consecutive revisions (v10, v11, v12) without being commissioned:
   domestic-agreement presumption; minor contractual capacity for the
   payslip obligation; the user's own unconfirmed claim that no law bars
   the parent-child contractual structure; whether the NCR-avoidance
   premise for excluding account-linking is accurate; and — new this
   revision — whether the pre-link independent-registration carve-out
   requires prior competent-person consent under POPIA. Confidence
   lowered to Low this revision, reflecting compounding, still-
   uncommissioned legal exposure.

2. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions)** — unresolved, carried forward
   unchanged from v11.

3. **Pre-link independent-registration carve-out — new this revision,
   characterized as an unresolved POPIA risk, not resolved.** A minor
   may now independently register and access one practice-only
   budgeting feature before any parent link exists. This reopens, in
   narrow form, a compliance question this case previously closed more
   broadly in v5 by collapsing all access behind a universal consent
   gate. Per direct instruction, this is not assumed compliant merely
   because it is narrower in scope; it is flagged for the specialist
   legal opinion (see Gap #1) and should not proceed to build or pilot
   ahead of that opinion's view.

4. **Late-penalty enforcement mechanism — technical question
   substantially answered in v11 (honor-system self-report, continue at
   launch); the underlying legal-enforceability question remains with
   the still-unobtained specialist legal opinion (see Gap #1).** This
   revision adds that the rationale for excluding account-linking
   (NCR-avoidance) is itself an unconfirmed premise, layering a further
   open sub-question onto the same unresolved gap rather than closing
   it.

5. **Child-development/age-appropriateness risk (Success Criteria,
   Risks, Validation Strategy)** — unchanged from v11; two residual
   pathways remain open (indirect parental-stress effects; payment-delay
   perception). The required expert review has not yet been conducted in
   any version of this case. Not directly addressed this revision — the
   pre-link carve-out is a data-privacy question, not a child-development
   one.

6. **Subscriber-count discrepancy (Revenue & Costs)** — unresolved,
   carried forward unchanged from v11.

7. **Request-for-payment feature inconsistency — RESOLVED in v11**,
   retained here for audit-trail continuity only.

8. **90-day vs. annual funnel tension — RESOLVED in v10**, retained here
   for audit-trail continuity only.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v11. Not addressed this revision.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Low (down from Medium) |
**Evidence:** Supported

**This revision reopens, in narrow form, a question this section
resolved in v5.** v5 closed the education-only direct-signup carve-out
by collapsing all access behind a universal parental-consent gate,
specifically to close off POPIA exposure from any pre-consent minor
access to the app. `Clarifications_v12.md` Item 3 reintroduces a narrower
version of exactly that pattern: independent minor registration, plus
access to one non-monetary, practice-only feature, before any parent link
exists. Per direct Chief of Staff instruction, the Incubator applies the
same directional compliance rigor here that it applied in v5, and does
not treat the narrower scope as self-evidently safe.

**Directional assessment (not a legal conclusion):** two distinct
questions are in play. First, does the act of independent account
registration itself — collecting whatever identifying data the
registration flow requires — constitute processing of a minor's personal
information under POPIA Section 1's broad definition, triggering the
Section 34/35 prior-consent requirement regardless of what the minor
subsequently does inside the app? This appears likely, though unconfirmed
by any specialist review. Second, does the practice/hypothetical income
data itself, once entered, constitute the minor's personal information
even though it does not reflect real financial circumstances? POPIA's
definition of personal information is not limited to financially
sensitive or "real" data — information about an identifiable, identified
data subject can qualify regardless of whether it is hypothetical in
content, particularly once tied to a persistent account. Neither question
is resolved by the fact that no real money or real task-earnings data is
involved pre-link, nor by the feature being singular rather than
comprehensive. Both are added to the specialist legal opinion's required
scope (see Legal & Compliance, Gap #1).

**Status remains Partial**, for this newly reopened reason in addition to
those unchanged from v9-v11: the universal consent-gate model's technical
mechanism is still undocumented; the two explicit user risk-accepted
assumptions (POPIA Section 14 retention sufficiency; exam-bonus
mechanic's no-schools-data-privacy-dimension assumption) remain accepted
but unreviewed by a specialist; Google Play's Families Policy loyalty-
point disclosure requirement and Apple's Kids Category IAP-currency
question remain open; the confirmed absence of ARB/NCR precedent for
"payslip"/"invoice"/"late penalty" terminology applied to minors is
unchanged; and now, the pre-link carve-out's POPIA posture is added as a
live, unresolved item rather than assumed closed. **Confidence is lowered
to Low** — not because the risk is newly severe in an absolute sense, but
because this section's assessment now depends on a question the case had
previously treated as settled (the value of the universal consent gate as
a clean line), and that settled understanding no longer fully holds.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 52% (67/130),
  unchanged from v11. Progression: 24% (v3) → 36% (v4) → 39% (v5) → 40%
  (v6) → 40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52%
  (v12).

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
is unchanged at 52% — this revision resolves two Outstanding Questions,
sharpens the specialist legal opinion's required scope for a third
consecutive time, corrects one internal contradiction (the "zero pre-link
access" claim), and — most substantively — characterizes a newly reopened
POPIA risk (the pre-link independent-registration carve-out) with the
same rigor applied to a comparable question in v5, without resolving it.
None of this moves a Status tag, so the score does not move; this is
stated explicitly so the unchanged score is not misread as this
revision's substance having been ignored. A v13 would need: (a) the
actual specialist legal opinion obtained, now carrying its largest scope
yet (contractual capacity; domestic-agreement presumption; NCR-avoidance
premise; pre-link carve-out POPIA posture); (b) resolution of the
family-vs-child install-count ambiguity; (c) resolution of the
subscriber-count discrepancy; (d) a user decision on the pre-link
practice-data retention question; and (e) the required child-development
review conducted, to meaningfully advance the Readiness Score further.
