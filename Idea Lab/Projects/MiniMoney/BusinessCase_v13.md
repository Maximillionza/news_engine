# Business Case: MiniMoney — v13

> Prepared by: Incubator. Source input: `00_CaseStudy.md` (verbatim user
> submission, 2026-07-05), `BusinessCase_v12.md` (prior version), and
> `ResearchFindings_v3.md` (Research House Engagement 3 — desk research on
> two narrow questions: whether mere minor account registration itself
> triggers POPIA processing/consent requirements independent of feature
> access, and whether the NCR actually regulates read-only account-linking
> as payment facilitation). This document is self-certified against the
> Incubator completion gate. Sections not touched by `ResearchFindings_v3.md`
> are carried forward as "Unchanged from v12" — since this Incubator's
> authorized inputs for this cycle are limited to `00_CaseStudy.md`,
> `BusinessCase_v12.md`, and `ResearchFindings_v3.md` only; no other prior
> version was read or used as a source.

> **Changes from v12 — summary of what this revision addresses:**
> `ResearchFindings_v3.md` delivers Supported-tier desk research on the two
> items that drove both Critical Legal sections' Confidence down to Low in
> v12. Per standing instruction, Research House's output is never trusted
> internal work product and is never Verified-tier regardless of how
> confident it sounds — it can only ever support raising a tag to
> Supported, and the Incubator applies its own scrutiny before deciding
> whether, and how far, to move any tag.
>
> **(1) Registration-itself-triggers-POPIA question.** Research House finds
> that POPIA's "processing" definition (Section 1) is broad enough to
> include mere collection/storage of a minor's data at registration, and
> that Section 34's prohibition attaches to "processing" as a whole, not to
> a feature-gated subset of it — a reasoning chain grounded in primary
> statutory text plus consistent secondary commentary, at Medium-High
> confidence for the statutory reading and Medium confidence for its
> application to this specific product design (no direct precedent found).
> This does **not** resolve the pre-link carve-out question in MiniMoney's
> favor — if anything, it substantiates the Incubator's own v12 directional
> concern that registration itself likely requires prior competent-person
> consent. What it does provide is a grounded, sourced basis for an
> assessment that was previously the Incubator's own unconfirmed reasoning
> alone. This is treated below as grounds for a **partial Confidence
> recovery** (Low to Medium) on both Critical Legal sections — the
> assessment is now better-evidenced, even though the substantive answer it
> points toward is unfavorable to the feature as currently scoped. Status
> remains Partial: no legal conclusion has been reached, no specialist
> opinion has been obtained, and the practice/hypothetical-data sub-
> question (whether non-real budgeting data is itself personal information)
> was confirmed by Research House as a **true gap** in publicly available
> guidance, not merely hard to find.
>
> **(2) NCR-payment-facilitation-premise question.** Research House finds,
> at Supported tier and Medium confidence, that none of the NCR's four
> registration categories (credit providers, credit bureaus, debt
> counsellors, Payment Distribution Agents) plausibly covers a read-only,
> non-custodial account-verification service — the closest category (PDAs)
> is specifically built around receiving and distributing consumer funds,
> which a read-only integration does not do. This is a reasonably strong,
> though not definitive, indication that the user's stated NCR-avoidance
> rationale for excluding Stitch/Mono (`Clarifications_v12.md` Item 2) may
> rest on a mistaken premise. This does not resolve the question outright —
> no NCR, FSCA, or SARB document was found addressing this exact service
> type by name — but it is new, sourced, Supported-tier information where
> v12 had only an unconfirmed user assumption. This is a genuine addition
> to the case's evidence base and is reflected below in Legal & Compliance,
> Risks, and a sharpened Outstanding Question.

## What Changed in v13 (Summary)

**Status:** Complete | **Confidence:** High | **Evidence:** Supported

1. **Legal & Compliance — Confidence recovers from Low to Medium.**
   Grounded in `ResearchFindings_v3.md`'s two Supported-tier findings, this
   is a genuine, evidence-based recovery, not merely time passing or scope
   quietly narrowing. The recovery is partial and explicitly bounded: the
   contractual-capacity claim, the domestic-agreement presumption, and the
   ARB precedent absence are entirely untouched by this research and
   remain at their prior evidentiary tiers. Status remains Partial — desk
   research is explicitly not a substitute for the still-uncommissioned
   specialist opinion, a limitation Research House itself states in both
   findings.

2. **Legal & Compliance — Child Data & Consent — Confidence recovers from
   Low to Medium, on the same basis.** The section's central open
   question (does independent registration itself trigger POPIA Section
   34/35) is now backed by a sourced, reasoned statutory analysis rather
   than the Incubator's own unaided inference. This is treated as an
   evidentiary improvement, not a risk reduction — the research findings
   point toward the carve-out being **more likely, not less likely,** to
   require prior consent as currently designed. Status remains Partial.

3. **Risks — trust/enforcement risk item sharpened, not resolved.** The
   NCR-avoidance premise underlying the exclusion of account-linking now
   has Supported-tier research suggesting it is likely mistaken, giving
   concrete weight to the "foregone opportunity" reading of this risk
   flagged in `reviews/DevilsAdvocate.md` (v12, Objection 2).

4. **Assumptions — the v12 assumption that the pre-link carve-out sits in
   a "materially lower-risk POPIA posture" than the broader carve-out
   closed in v5 is now directly challenged, not supported, by this
   revision's research**, and is reframed accordingly.

5. **Outstanding Questions — two items reframed from "unconfirmed premise"
   to "substantially informed by desk research, still not specialist-
   confirmed."** Neither is removed from the open list; both are updated
   with what the research found and what it explicitly could not find.

**Net effect on Readiness Score: none.** No section's Status changes this
revision — this research informs the still-uncommissioned specialist
opinion but does not substitute for it, per Research House's own repeated
caveats and per the Incubator's own scrutiny of that vendor output.
Consistent with the playbook principle that analytical and evidentiary
improvements do not automatically move a Status-only Readiness Score, this
is stated explicitly. Unlike v12 — where Confidence fell on both Critical
sections — this revision's Confidence moves in the **opposite direction**
on the same two sections, recovering from Low to Medium. This is also
stated explicitly, consistent with the playbook practice of tracking
Confidence trajectory as its own signal distinct from the Readiness Score,
in either direction. **Readiness Score: 67/130 = 51.5%, rounded to 52%,
unchanged from v12.**

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
child has zero visibility into it. A minor cannot access any *substantive*
part of the app — task assignment, earnings, payslip, invoice, or store —
without a pre-existing, consenting parent account; however, a minor
**may** independently download, install, and register an account, and
before any parent link exists, that account can access exactly one
feature (a "budgeting" tool for manually-entered practice income) — a
narrow exception to the otherwise-universal consent gate, not an absolute
rule.

**This revision incorporates Research House's third engagement — two
narrow desk-research findings, both Supported-tier, that inform without
resolving the case's two highest-priority open legal questions.** First,
research on whether mere minor account registration triggers POPIA's
consent requirements found that the statutory "processing" definition and
Section 34's prohibition plausibly attach at the point of registration
itself, independent of subsequent feature access — a finding that
**substantiates, rather than dissolves**, the pre-link carve-out risk this
case flagged as unresolved in v12. Second, research on whether the NCR
actually regulates read-only account-linking (the stated rationale for
excluding Stitch/Mono) found that none of the NCR's four registration
categories plausibly covers a read-only, non-custodial service — a
reasonably strong, though not definitive, indication that MiniMoney may be
excluding a potentially compliant, enforcement-risk-reducing feature based
on a mistaken premise. Neither finding is a legal conclusion, and both are
explicitly framed by Research House as informing, not replacing, the still
-uncommissioned specialist legal opinion. On the strength of this
grounded, sourced research, both Critical Legal sections' Confidence
recovers from Low to Medium this revision — a genuine evidentiary
improvement, not a resolution of the underlying risks, one of which (the
registration-consent question) the research makes look **more** likely to
be a real compliance obligation, not less. The Readiness Score is
unchanged at **52% (67/130)** — no Status moved this revision.

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed by `ResearchFindings_v3.md`.

## Opportunity

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Objectives

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Success Criteria

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Stakeholders

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Target Users/Customers

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Value Proposition

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Market & Competition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Business Model

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Revenue & Costs

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision. The unreconciled
subscriber-count discrepancy remains open (see Outstanding Questions).

## Operations

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. `ResearchFindings_v3.md` does not address the
undocumented pre-link practice-data retention question (what happens to
manually-entered practice data once a parent links and the feature
auto-populates with real earnings) — that item was not in this
engagement's scope and remains an open Outstanding Question. Confidence
remains at Medium, not restored to High, for that unchanged reason.

## Technology

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Legal & Compliance ★ (Critical)

**Status:** Partial | **Confidence:** Medium (up from Low) |
**Evidence:** Supported

**This section remains flagged Critical and its Status is unchanged.**
The underlying legal uncertainty — money-transmitter characterization of
the invoice/payment trigger; the absence of ARB/NCR precedent for
"payslip"/"invoice"/"late penalty" terminology applied to minors; POPIA
Section 34/14 sufficiency — is unresolved, and the specialist legal
opinion required to address it has still not been obtained. **Confidence
is raised this revision from Low to Medium**, reversing the v12 downgrade,
on the specific and bounded basis of `ResearchFindings_v3.md`'s two
Supported-tier findings, detailed below. This is a genuine evidentiary
recovery — real desk research was conducted, grounded in primary statutory
and regulatory text, addressing exactly the two items that caused the v12
downgrade — not a reversion driven by time passing or by scope narrowing.
It is explicitly **not** a Status change: neither finding is a legal
conclusion, both are self-described by Research House as inputs to the
still-uncommissioned specialist opinion rather than substitutes for it,
and the opinion's required scope (contractual capacity; domestic-agreement
presumption; NCR-avoidance premise; pre-link carve-out's POPIA posture)
is unchanged in breadth from v12.

**Minor contractual capacity — untouched by this revision.** This item
was not in `ResearchFindings_v3.md`'s scope. The structural design
(payment obligation runs against the parent, documented at Verified-tier
as a design fact) and the user's separate legal-research claim ("no law or
act prevents" the structure, documented at Assumed-tier) remain exactly as
stated in v12, pending specialist confirmation.

**Read-only account-linking exclusion — NCR-avoidance premise now
Supported-tier questioned, not resolved.** `ResearchFindings_v3.md` Item 2
finds that NCR registration is anchored to four defined categories (credit
providers, credit bureaus, debt counsellors, Payment Distribution Agents),
none of which plausibly describes a read-only, non-custodial
account-verification service — PDAs, the closest conceptual match, exist
specifically to receive and distribute consumer funds, which such a
service does not do. Sourced commentary (ENS Africa) further confirms
South Africa has no PSD2-equivalent regime and that no regulator,
including the NCR, is currently identified as exercising binding oversight
over account-information or payment-initiation service providers ahead of
the still-developing Open Finance framework (consistent with Engagement
2's prior finding). This is a reasonably strong, though not definitive,
indication that the user's stated rationale for excluding Stitch/Mono may
rest on a mistaken premise — MiniMoney may be forgoing a feature that
could reduce its honor-system enforcement risk (see Risks) based on a
regulatory concern that does not, on the evidence found, actually apply.
This is documented at **Supported**-tier (raised from the prior
Assumed-tier characterization of the premise itself, though the premise's
ultimate accuracy remains for the specialist opinion to confirm) and
remains a required item for that opinion.

**Pre-link independent-registration carve-out — Supported-tier research
now substantiates the concern, not the safety, of this feature.**
`ResearchFindings_v3.md` Item 1 finds that POPIA's "processing" definition
is broad enough to include mere collection/storage of a minor's data
(name, age/date of birth, possibly email) at the point of registration,
and that Section 34's prohibition attaches to "processing" as a whole —
meaning the general prohibition would, on the statutory text and
consistent secondary commentary, plausibly apply at registration itself,
independent of what feature the minor subsequently accesses. This is the
same directional read the Incubator itself reached in v12 without any
sourced backing; it is now grounded in primary statutory text (POPIA
Sections 1, 34, 35) and cross-checked secondary commentary (VDT Attorneys,
MJ Kotze Inc, POPIApack, ITLawCo), at Medium-High confidence for the
statutory reading and Medium confidence for its application to this
specific "registration-before-parent-link" product design, since no direct
precedent addresses that exact scenario. **This does not resolve the risk
in MiniMoney's favor — it substantiates it.** Separately,
`ResearchFindings_v3.md` explicitly confirms it could find **no source**
distinguishing "hypothetical/practice" data from "real" financial data as
a POPIA-relevant category, and characterizes this as a **true gap in
publicly available guidance**, not merely a hard-to-find answer — meaning
the second sub-question (whether practice-only budgeting data is itself
personal information) remains genuinely unresolved and cannot be
Confidence-upgraded on the strength of this engagement. Both remain
required items for the specialist legal opinion and are separately
documented in Legal & Compliance — Child Data & Consent below.

**Redesigned mechanic implications — unchanged from v12.** The
late-penalty mechanic being parent-incurred and parent-invisible-only
changes, but does not resolve, the terminology-to-minors risk: "invoice,"
"payslip," and "arrears" language is still applied in a product
explicitly directed at minors as young as 6.

The feature-level gating plan established in v9 (financial-trigger
features locked behind the opinion; foundational rails may proceed in
parallel) is unchanged and still applies, including the pre-link
independent-registration carve-out's gate — this research strengthens, if
anything, the case for keeping that gate in place rather than loosening
it.

## Risks

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Carried forward from v12, with two updates:

**Trust/enforcement risk — NCR-avoidance premise now Supported-tier
likely mistaken, sharpening this risk's "foregone opportunity" framing.**
v12 flagged that the case may be foreclosing a feature (account-linking)
that could reduce enforcement risk, based on an unverified regulatory
assumption. `ResearchFindings_v3.md` Item 2 provides Supported-tier
research indicating that assumption likely does not match what NCR
registration actually covers. This does not change the risk's category or
its Status, but it gives concrete, sourced weight to the reading
`reviews/DevilsAdvocate.md` (v12, Objection 2) raised — that this is a
real, quantifiable foregone-opportunity cost, not merely a symmetrically
unconfirmed claim alongside the contractual-capacity question. The
Incubator does not treat this as resolved; the user has not yet been asked
whether they wish to revisit the exclusion decision in light of this
finding (see Outstanding Questions).

**Pre-link independent-registration carve-out risk — Supported-tier
research increases, not decreases, the estimated likelihood this risk
materializes as described.** v12 characterized this as a live, unresolved
POPIA risk without a directional lean either way beyond the Incubator's
own reasoning. `ResearchFindings_v3.md` Item 1 provides sourced statutory
grounding for the view that registration itself likely triggers POPIA's
consent requirement, independent of the practice-only nature of the
subsequent feature. This is a sharpening of the risk's estimated
probability, not a resolution — the risk remains open pending the
specialist opinion, and the practice-data-as-personal-information
sub-question remains a confirmed gap in available guidance.

The undocumented data-retention handling for pre-link practice data (see
Operations) remains unchanged and unaddressed by this engagement.

## Assumptions

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12, with one revision:

**The v12 assumption that "a narrow, single-feature, practice-data-only
pre-link carve-out sits in a materially lower-risk POPIA posture than the
broader education-only carve-out this case closed in v5" is now directly
challenged by `ResearchFindings_v3.md`, not supported by it.** The
research suggests the operative trigger for POPIA's Section 34/35
prohibition is the act of registration/data-collection itself, not the
scope or "reality" of what a minor subsequently does inside the app —
meaning the narrower feature scope may not be the risk-reducing factor the
original assumption supposed. This assumption is retained in the case
record for audit-trail continuity but is now flagged as **likely
inaccurate, pending specialist confirmation**, rather than merely
unconfirmed. It should not be relied upon in any near-term product
decision.

The contractual-capacity research-claim assumption from v12 is unchanged
by this revision — not addressed by `ResearchFindings_v3.md`.

## Constraints

**Status:** Complete | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Roadmap

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision. The specialist legal
opinion's commissioning trigger remains "event-based, once a stable
working model exists," a point `reviews/DevilsAdvocate.md` (v12,
Objection 4) questioned directly; this revision's research does not
change that trigger and the same question stands.

## Financial Considerations

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision. The family-vs-child
install-count ambiguity and the unreconciled subscriber-count discrepancy
remain open (see Outstanding Questions).

## Validation Strategy

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

1. **Legal validation** — the specialist opinion's required scope is
   unchanged in breadth from v12, but this revision supplies it with two
   sourced, Supported-tier desk-research inputs (registration-triggers-
   POPIA reasoning; NCR-scope reasoning) it did not previously have. The
   opinion itself remains unobtained. Given that three consecutive
   Business Case revisions (v10, v11, v12) sharpened this opinion's scope
   without commissioning it, and this revision — while not sharpening
   scope further — still has not triggered commissioning despite now
   having two grounded research inputs ready to hand to counsel, the
   Incubator repeats, without prescribing a decision, that the
   "event-based" trigger may warrant reconsideration as a dated one.
2. **Primary user-research validation** — unchanged from v12.
3. **Child-development/age-appropriateness review** — unchanged from
   v12; not addressed by this revision's research.
4. **Trust/enforcement and dispute-mechanism validation** — unchanged
   from v12. The NCR-avoidance premise now being Supported-tier
   questioned does not substitute for empirical pilot validation of
   whether parents and children find the honor-system model trustworthy
   in practice.
5. **Market/demand validation** — unchanged from v12.
6. **Pricing/conversion validation** — unchanged from v12.
7. **Curriculum validation** — unchanged from v12.
8. **Pre-link carve-out compliance validation** — required scope
   unchanged from v12 (specialist confirmation of whether independent
   minor registration and practice-data entry requires prior
   competent-person consent), now informed by `ResearchFindings_v3.md`
   Item 1's sourced statutory reasoning, which leans toward "yes, likely."
   This strengthens rather than removes the requirement that this feature
   not proceed to build or pilot ahead of the specialist opinion.

## Supporting Evidence

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged in content and treatment from v12, with one addition:
`ResearchFindings_v3.md` (Research House Engagement 3) is added as new
supporting evidence, documented at **Supported**-tier per Research House's
own self-assessed evidence tier for both findings, consistent with
standing instruction that vendor research can support a Supported-tier
tag but never Verified. Both findings are explicitly self-limited by
Research House as informing, not resolving, the underlying legal
questions — neither finding is treated here as closing any open item.

## Outstanding Questions

**Status:** Complete | **Confidence:** High | **Evidence:** Verified

**Substantially informed by desk research this revision, not resolved
(retained on the open list, updated with what was found):**

- Does the specialist legal opinion confirm or refute the user's premise
  that read-only account-linking (Stitch/Mono) would trigger NCR
  payment-facilitation obligations? `ResearchFindings_v3.md` provides
  Supported-tier, Medium-confidence research indicating this premise
  likely does not match what NCR registration actually covers (none of
  its four categories fits a read-only, non-custodial service). No
  NCR/FSCA/SARB document was found naming this service type explicitly.
  The specialist opinion remains required to close this question formally.
  (Legal & Compliance, Risks)
- Does independent minor account registration — before any parent link
  exists — itself constitute processing of a minor's personal
  information under POPIA, requiring prior competent-person consent?
  `ResearchFindings_v3.md` provides Supported-tier, Medium-to-Medium-High
  confidence research indicating this is likely, grounded in POPIA's broad
  "processing" definition and Section 34's unqualified prohibition. No
  direct precedent was found addressing this exact "registration-before-
  parent-link" product design. The specialist opinion remains required to
  close this question formally. (Legal & Compliance, Legal & Compliance —
  Child Data & Consent)

**Unresolved, confirmed as a true gap in available guidance this
revision:**

- Does manually-entered practice income data in the pre-link budgeting
  feature constitute the minor's personal information under POPIA, even
  though it is hypothetical and does not reflect real earnings?
  `ResearchFindings_v3.md` explicitly could not find any source
  distinguishing hypothetical/practice data from real data for this
  purpose, and characterizes this as a true gap in publicly available
  guidance, not merely hard to find. (Legal & Compliance — Child Data &
  Consent)

**New this revision:**

- Given `ResearchFindings_v3.md`'s finding that the NCR-avoidance premise
  for excluding account-linking may be mistaken, does the user wish to
  revisit that exclusion decision, or does the user want to wait for the
  specialist opinion's formal confirmation before reconsidering it? (Legal
  & Compliance, Risks, Roadmap)

**Still open, carried forward unchanged from v12:** what happens to a
minor's manually-entered practice data once a parent account links and the
feature auto-populates with real earnings (discarded, retained, or
overwritten); with the specialist legal opinion's required scope now
partly informed by two rounds of sourced desk research without itself
being commissioned, whether the user wants to revisit the "event-based,
once a stable working model exists" trigger in favor of a dated
commissioning trigger; the family-vs-child install ambiguity; the
unreconciled subscriber-count discrepancy (180-1,830 computed vs.
360-2,440 cited); the recommended preliminary legal read's adoption
decision; fund custody mechanics; consent-gate technical mechanism; task
verification; dispute-escalation beyond 48 hours; payment-routing
timeline; late-penalty cap rationale; Fintech Advance scope; exam-bonus
data source; Mbucks-peg flexibility; curriculum age-band splits; app-store
policy sub-questions; MoneyAfrica Kids' unpublished premium price; whether
informal engineering-cost quotes will be sought; the external-help budget
ceiling; the schools-partnership channel's timeline/target school
count/resourcing plan; the domestic-agreement presumption's application to
MiniMoney's "agreed condition of budget setup" framing.

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

Points earned: **67** (unchanged from v12 — no Status changed this
revision).

Points possible = 22 non-critical sections × 5 = 110, plus 2 critical
sections × 5 × 2 = 20. **Total possible = 130** (unchanged).

**Readiness Score = 67 / 130 = 51.5%, rounded to 52%. Unchanged from
v12.**

No section is Critical + Incomplete: Legal & Compliance and Child Data &
Consent are both Partial.

Progression across versions: 24% (v3) → 36% (v4) → 39% (v5) → 40% (v6) →
40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52% (v12) →
**52% (v13).**

### Critical Gaps

1. **Legal & Compliance / Child Data & Consent (Critical, Partial)** —
   the specialist POPIA/ARB/contract-law legal opinion remains
   unobtained. Its required scope is unchanged in breadth from v12
   (domestic-agreement presumption; minor contractual capacity for the
   payslip obligation; the user's own unconfirmed claim that no law bars
   the parent-child contractual structure; the NCR-avoidance premise for
   excluding account-linking; whether the pre-link independent-
   registration carve-out requires prior competent-person consent under
   POPIA), but two of these items are now backed by Supported-tier desk
   research rather than resting entirely on unconfirmed user or Incubator
   assessment. Confidence recovers this revision from Low to Medium on
   both Critical sections, reflecting genuine evidentiary progress —
   though this is a partial recovery, not a resolution: the specialist
   opinion is still not commissioned, and the research findings, where
   substantive, point toward the pre-link carve-out being **more** likely
   a real compliance problem, not less.

2. **Family-vs-child install ambiguity (Financial Considerations,
   Revenue & Costs, Assumptions)** — unresolved, carried forward
   unchanged from v12.

3. **Pre-link independent-registration carve-out — remains an unresolved
   POPIA risk; this revision's research substantiates rather than
   dissolves the concern.** A minor may still independently register and
   access one practice-only budgeting feature before any parent link
   exists. `ResearchFindings_v3.md` provides sourced statutory grounding
   for treating registration itself as likely triggering POPIA's consent
   requirement, and confirms the practice-data-as-personal-information
   sub-question as a true, unresolved gap in available guidance. This
   remains flagged for the specialist legal opinion (see Gap #1) and
   should not proceed to build or pilot ahead of that opinion's view.

4. **Late-penalty enforcement mechanism — technical question
   substantially answered in v11 (honor-system self-report, continue at
   launch); the underlying legal-enforceability question remains with
   the still-unobtained specialist legal opinion (see Gap #1).** This
   revision adds Supported-tier research suggesting the rationale for
   excluding account-linking (NCR-avoidance) is likely mistaken —
   sharpening, without resolving, whether MiniMoney is forgoing a feature
   that could otherwise reduce this same enforcement risk.

5. **Child-development/age-appropriateness risk (Success Criteria,
   Risks, Validation Strategy)** — unchanged from v12; not addressed by
   this revision's research.

6. **Subscriber-count discrepancy (Revenue & Costs)** — unresolved,
   carried forward unchanged from v12.

7. **Request-for-payment feature inconsistency — RESOLVED in v11**,
   retained here for audit-trail continuity only.

8. **90-day vs. annual funnel tension — RESOLVED in v10**, retained here
   for audit-trail continuity only.

## Operations — Curriculum Design (Domain Extension)

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Unchanged from v12. Not addressed this revision.

## Legal & Compliance — Child Data & Consent (Domain Extension) ★ (Critical)

**Status:** Partial | **Confidence:** Medium (up from Low) |
**Evidence:** Supported

**Confidence is raised this revision from Low to Medium**, reversing the
v12 downgrade, on the basis of `ResearchFindings_v3.md` Item 1's
Supported-tier statutory research. This section's central open question —
whether independent minor account registration itself, absent any
subsequent feature access, constitutes processing of a minor's personal
information under POPIA Section 34/35 — is now grounded in sourced
primary-text analysis (POPIA Section 1's broad "processing" definition;
Section 34's unqualified prohibition attaching to processing as a whole)
plus consistent secondary commentary (VDT Attorneys, MJ Kotze Inc,
POPIApack, ITLawCo), at Medium-High confidence for the statutory reading
itself and Medium confidence for its application to MiniMoney's specific
registration-before-parent-link design, since no direct precedent or
Information Regulator guidance addresses that exact scenario. **This
Confidence recovery reflects the quality of the evidence now available to
the assessment, not a reduction in the underlying risk** — the research
points toward the carve-out being more likely, not less likely, to require
prior competent-person consent as currently designed.

**Directional assessment, updated:** the first of the two questions this
section carried since v12 (does registration itself trigger Section 34/35,
independent of feature access) is now Supported-tier substantiated as
"appears likely," consistent with, and strengthening, the Incubator's own
v12 reasoning. The second question (does practice/hypothetical budgeting
data itself constitute the minor's personal information) is **confirmed
by Research House as a true gap in publicly available guidance** — no
source found draws this distinction one way or the other — and therefore
remains at its prior evidentiary footing, not upgradeable on the strength
of this engagement. Both remain required items for the specialist legal
opinion (see Legal & Compliance, Gap #1).

**Status remains Partial**, for the reasons unchanged from v9-v12: the
universal consent-gate model's technical mechanism is still undocumented;
the two explicit user risk-accepted assumptions (POPIA Section 14
retention sufficiency; exam-bonus mechanic's no-schools-data-privacy
dimension assumption) remain accepted but unreviewed by a specialist;
Google Play's Families Policy loyalty-point disclosure requirement and
Apple's Kids Category IAP-currency question remain open; the confirmed
absence of ARB/NCR precedent for "payslip"/"invoice"/"late penalty"
terminology applied to minors is unchanged; and the pre-link carve-out's
POPIA posture, while now better-evidenced, remains formally unresolved
pending the specialist opinion.

## Self-Certification Against Completion Gate

- Every section tagged with Status/Confidence/Evidence: **Yes.**

- No section is Critical + Incomplete: **Yes — PASSES.** Legal &
  Compliance and Legal & Compliance — Child Data & Consent are both
  Partial.

- Readiness Score ≥ 70%: **No — FAILS.** Score is 52% (67/130),
  unchanged from v12. Progression: 24% (v3) → 36% (v4) → 39% (v5) → 40%
  (v6) → 40% (v7) → 47% (v8) → 47% (v9) → 49% (v10) → 52% (v11) → 52%
  (v12) → 52% (v13).

- Expert roster entries ≥3 sentences, each naming a specific case-study
  assumption: see `ExpertRoster.md`, regenerated this cycle.

- Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle.

- ExecutiveSummary.md generated per fixed format: see
  `ExecutiveSummary.md`, regenerated this cycle.

**This Business Case does not currently pass its own completion gate.**
The Critical + Incomplete condition remains cleared. The Readiness Score
is unchanged at 52% — this revision incorporates two Supported-tier
Research House findings that substantiate, rather than resolve, the
pre-link carve-out and NCR-avoidance-premise questions, and on that basis
recovers both Critical Legal sections' Confidence from Low to Medium.
This is a genuine evidentiary improvement, distinct from and not
reflected in the Readiness Score, which tracks Status only — this is
stated explicitly so the unchanged score is not misread as this
revision's research having added nothing. A v14 would need: (a) the
actual specialist legal opinion obtained, now able to draw on two rounds
of sourced desk research in addition to its original scope; (b)
resolution of the family-vs-child install-count ambiguity; (c) resolution
of the subscriber-count discrepancy; (d) a user decision on the pre-link
practice-data retention question; (e) a user decision on whether to
revisit the account-linking exclusion given this revision's NCR findings;
and (f) the required child-development review conducted, to meaningfully
advance the Readiness Score further.
