# Investment Committee Full Review — MiniMoney v20

**Reviewed:** `ExecutiveSummary.md` (v20) and `BusinessCase_v20.md` only.
No other file in the case folder was opened. This is the Investment
Committee's independent review; nothing here is inherited from any
Incubator working file.

---

## PASS 1 — High-Level Review (ExecutiveSummary.md only)

### What the Executive Summary reveals

MiniMoney is a South African, Android-first financial-education app for
children/teens 6-18. It combines a gamified task system with a
simulated payroll (Mbucks, real-money-pegged, non-custodial — the parent
pays the child directly through their own banking app) and a separate
cosmetic-currency layer (Mpoints). Subscription-only at R59.99/month per
family (up to 4 children), organic-only acquisition at launch (decided
this cycle), a R10,000 total development budget, a 6-month runway, and a
now-stated-but-uncosted "self-fund further" contingency. The Readiness
Score sits at 70.0% (91/130) — flat across two cycles, clearing the
completion gate with no margin. Six Investment Committee required
changes from a prior cycle are reported resolved; curriculum authorship
is explicitly named as still undecided; two items (an exam-bonus
motivation-probe and a data-breach/incident-response commitment) are
described as Incubator-drafted candidates awaiting specialist review,
not yet obtained.

### Provisional panel assembled (fresh, from domain signals in the ES only)

The Executive Summary spans at least six distinct expert domains, each
independently load-bearing:

1. **FinTech & Payments Regulatory Counsel** — the entire non-custodial
   model, Mbucks non-transferability, and money-transmitter risk posture
   are legal/regulatory questions signaled directly in the ES.
2. **Child Development / Behavioral Psychology Specialist** — the
   exam-bonus hybrid, late-penalty mechanic, and a "motivation-probe"
   pending specialist review all concern psychological effects on minors.
3. **Data Privacy Specialist** — a "data-breach/incident-response
   commitment" pending specialist review, for a product collecting
   children's data, is a distinct competency from general legal counsel.
4. **EdTech / Curriculum Specialist** — this is explicitly a financial-
   education product; the ES flags curriculum authorship as an
   unresolved open decision.
5. **Venture/Financial Analyst** — R10,000 budget, 6-month runway,
   uncosted self-fund contingency, subscription unit economics.
6. **South African Consumer Market Analyst** — organic-only acquisition
   against an installs funnel, SA-specific demand and competitive
   context.

This panel is assembled fresh from what the domain evidently requires,
not from any roster the Incubator may have produced.

### Provisional view

**Genuinely uncertain, leaning cautious.** The Executive Summary reads
as an honest, self-aware document — it names its own open items rather
than papering over them (curriculum authorship "explicitly open,"
motivation-probe and data-breach commitment both labeled "Evidence:
Assumed, pending specialist review"). That candor is a positive signal.
But three things in the ES itself raise a provisional flag before any
detail is read: (a) the Readiness Score has been flat at 70.0% for two
consecutive cycles and clears the gate "with no margin" — any downward
recalculation would fail it; (b) the "self-fund further" contingency is
explicitly "directional, not costed," which on its face is not a
contingency in any operational sense, only a stated intention; (c) two
specialist reviews (child-development, data-privacy) are described as
pending but not required to close the Investment Committee's own prior
items — meaning content that touches children's psychology and
children's data is going forward on non-specialist-reviewed drafts.

### What Pass 2 needs to confirm or overturn

- Whether the "no margin" 70% score is robust to scrutiny, or whether
  internal inconsistencies in the Business Case's own scoring logic
  would move it below threshold.
- Whether the uncosted self-fund contingency and the undecided
  curriculum authorship are treated as genuinely resolved decisions, or
  as decisions in name only.
- Whether skipping specialist review of child-facing instrumentation and
  a children's-data breach protocol before pilot is adequately justified
  or is a real gap.
- Whether organic-only acquisition is a supportable strategy against the
  stated 18,000-61,000 install funnel, or an untested load-bearing
  assumption.

---

## PASS 2 — Full Review (BusinessCase_v20.md)

### Expert 1: FinTech & Payments Regulatory Counsel

**Assessment.** The legal foundation (Legal & Compliance ★, §"Legal &
Compliance") is the strongest section in the case. Money-transmitter
risk is assessed low and contingent on a locked, enforceable
product-spec constraint (Mbucks non-transferability); minor contractual
capacity is now fully resolved with the Conradie v Rossouw citation
closed; NCR inapplicability is confirmed. This is real legal work, not
a placeholder.

**Strengths.** Seven originally-scoped legal questions all answered at
Verified tier (Legal & Compliance). The contingent nature of the
low-risk finding is stated plainly, not buried — any roadmap change to
Mbucks transferability triggers a mandatory re-analysis (Value
Proposition, Business Model, Constraints).

**Weaknesses.** Reliance on a single retained lawyer's opinion with no
second opinion sought, for a product whose central risk-mitigation
argument (terminology risk, §5) is acknowledged to have "no ARB ruling
addresses this fact pattern" — MiniMoney would be a first test case if
challenged. That is a materially different risk posture than "resolved."

**Risks.** Two regulator questions remain externally unsettled (SARB/NPS
Act on account-linking; FPB classification on Mpoints), both with
owners and fallbacks, but the fallbacks are not cost-free: the FPB
fallback removes the entire Mpoints/cosmetic-store layer, "weakening
the 6-9 tier's immediate-feedback loop" (Legal & Compliance,
"No-Mpoints launch configuration" ripple trace) — a real product-quality
degradation, not a neutral contingency.

**Opportunities.** The non-custodial design is validated by international
precedent (FamZoo, Bomad — Market & Competition) as a structurally sound,
non-outlier model.

**Missing Information.** No second legal opinion on the terminology-risk
first-mover exposure; no cost estimate for what happens operationally if
both fallbacks (no-linking, no-Mpoints) trigger simultaneously.

**Recommendations.** Treat the FPB and SARB rechecks as genuinely
schedule-critical, not "eventually" — both currently sit at build-spec
stage with no date attached.

**Confidence Level:** High (for what has been reviewed); Medium overall
given the two open regulatory dependencies.

**Support Recommendation:** Proceed with Changes.

---

### Expert 2: Child Development / Behavioral Psychology Specialist

**Assessment.** The design work that exists (Operations; Success
Criteria's family-relationship-strain measurement package, sourced from
validated instruments — PSI-SF, FAD-GFS, abbreviated CPRS) reflects real
specialist input from a prior cycle (`ChildDevelopmentReview_v1.md`,
cited). The exam-bonus hybrid is a defensible compromise design. But the
newest addition — the motivation-probe — is Incubator-drafted, not
specialist-drafted (Success Criteria).

**Strengths.** The late-penalty redesign (grace period, parent-only
visibility) is a genuine source-reduction mitigation, not just tracking.
Age-stratified measurement bands (6-9, 10-14, 15-18) show real design
maturity.

**Weaknesses.** The motivation-probe intended to detect whether the
retained outcome-contingent exam bonus is crowding out intrinsic
motivation in children is, by the document's own admission, "not yet
reviewed by the child-development specialist... that review is flagged
as a recommended next step, not a completed one" (Success Criteria).
This is precisely the instrument meant to catch the one specialist-named
residual risk in the entire case — running it unreviewed inverts the
purpose of specialist oversight.

**Risks.** If the probe's wording is poorly calibrated (a real risk for
lay-drafted child-facing psychological instruments, especially the 6-9
picture/simple-language variant, Success Criteria), the pilot could
produce a false negative on the one risk everyone agrees is real but
unresolved — and that false negative would then be treated as validating
evidence for a permanent design decision.

**Opportunities.** Near-zero marginal cost to run the review before pilot
enrollment (Roadmap: "Pilot" phase) — this is a cheap fix relative to its
downside if skipped.

**Missing Information.** No committed date for the specialist review; no
statement of what happens to the pilot if the review isn't completed in
time — proceed anyway, or hold enrollment.

**Recommendations.** Make the child-development specialist's review of
the motivation-probe a hard pre-enrollment gate, not a "recommended next
step" (currently Roadmap, Outstanding Questions).

**Confidence Level:** Medium.

**Support Recommendation:** Proceed with Changes.

---

### Expert 3: Data Privacy (POPIA) Specialist

**Assessment.** The consent-model finding (POPIA s34/s35(1)(a), Legal &
Compliance §2, and the Child Data & Consent domain extension) is solid
and specialist-sourced. The new data-breach/incident-response commitment
is not: it is "a founder-authored draft, not yet reviewed by the
Data-Privacy Practitioner" (Constraints), explicitly Evidence: Assumed.

**Strengths.** The candidate breach commitment's content is reasonably
well-constructed for a lay draft — it correctly anchors to POPIA s22
notification obligations and correctly avoids inventing a GDPR-style
72-hour clock the statute doesn't require (Constraints).

**Weaknesses.** The document itself states the specialist review is
"advisable... though not required to close this Investment Committee
item" (Constraints, Roadmap, Child Data & Consent extension) — meaning
this stayed intentionally unreviewed to satisfy a prior Investment
Committee condition on paper, not because a genuine risk assessment
concluded review was unnecessary.

**Risks.** POPIA s14 retention period/deletion trigger remains
undesigned (Legal & Compliance §3, Outstanding Questions) — a build task,
not yet done. Combined with the unreviewed breach protocol, there is a
real possibility that actual children's personal information will be
collected during the pilot (Roadmap: pilot phase) before either the
retention design or the breach protocol has been checked by anyone with
POPIA-specific minors expertise.

**Opportunities.** None of this requires new spend — the practitioner
review is stated as zero marginal cost, same as the legal opinion
already obtained.

**Missing Information.** No retention-period figure proposed even as a
draft; no committed timeline for practitioner review relative to pilot
data collection start.

**Recommendations.** Require the Data-Privacy Practitioner's review of
both the breach commitment and the POPIA s14 retention design before any
real child's data is collected — i.e., before pilot enrollment, not
merely "during" the build phase as currently stated (Roadmap).

**Confidence Level:** Medium-Low, specifically because the one item this
specialist would need to sign off on has not been signed off.

**Support Recommendation:** Proceed with Changes.

---

### Expert 4: EdTech / Curriculum Design Specialist

**Assessment.** For a product whose own Problem section states "7 of 10
[interviewed families] expressed interest specifically in the education
aspect," the curriculum — the actual educational content — does not
exist, and as of this cycle, who will author it is an open question
(Curriculum Design domain extension; Roadmap; Critical Gap #6).

**Strengths.** The three-tier age framework (early childhood, pre-teen,
teens) is a coherent structural starting point, and Fintech Advance's
gamification-avoidance/risk-literacy framing decision (Value Proposition,
per `ChildDevelopmentReview_v1.md` Q5) is a sound, specialist-informed
call.

**Weaknesses.** Authorship is now explicitly undecided between the
founder personally authoring it or engaging a designer under a
zero-marginal-cost policy whose scope was never confirmed to cover
instructional design (Curriculum Design; Outstanding Questions). This is
not a minor build-spec parameter — it is the identity of the person who
will produce the product's namesake deliverable, and it is unresolved
while the workstream is simultaneously described as "starting now"
(Roadmap) in parallel with a 6-month runway that is already tight.

**Risks.** If the zero-marginal-cost advice policy does not, in fact,
extend to curriculum/instructional design (a real possibility the
document itself flags as unconfirmed), the founder inherits an unplanned
either-cost or an unplanned-workload item mid-runway, on top of build,
regulatory rechecks, and pilot execution — all already assessed as the
case's binding constraint (Financial Considerations, Risks:
execution-capacity).

**Opportunities.** `CurriculumDraft_v1.md` exists as an unreviewed
starting point (Roadmap) — meaning the founder is not starting from zero
in wall-clock terms once authorship is decided.

**Missing Information.** No decision deadline is stated for authorship;
no fallback described if neither self-authoring nor the advice-policy
route proves viable in time.

**Recommendations.** Decide curriculum authorship — or set a hard
decision date within the current cycle — before further runway elapses;
an undecided "who" on a "starting now" workstream is a scheduling risk
disguised as an open question.

**Confidence Level:** Low, specific to this section only — the rest of
the product design is coherent, but the core educational deliverable is
unauthored and unowned.

**Support Recommendation:** Proceed with Changes.

---

### Expert 5: Venture/Financial Analyst

**Assessment.** The financial picture is candid about its own thinness
(Financial Considerations, Revenue & Costs), which is a strength in
honesty but does not change the underlying resourcing exposure. R10,000
against a previously-cited $25,000-$120,000+ agency reference range
(45×-220× gap) is coherent only if the founder's own unpaid labor and AI
tooling substitute entirely for professional engineering capacity
(Revenue & Costs).

**Strengths.** The runway, not the cash budget, is correctly identified
as the binding constraint (Constraints, Financial Considerations) — this
is the right way to frame a solopreneur venture's real limiting resource
(time, not money).

**Weaknesses.** The "self-fund further" runway-slippage contingency
(Constraints, Financial Considerations, Critical Gap #1) has no stated
amount, no maximum extension period, and no defined trigger threshold
beyond "month 6 arrives unfunded, or any workstream slips." As a risk
mitigant this is functionally indistinguishable from having no
contingency at all — it commits to a direction, not a magnitude, and the
document's own Constraints section still scores this as contributing to
a "Complete" status.

**Risks.** Revenue projections (Revenue & Costs: R10,798-R109,782/month
run-rate range) rest on a Year-1 paying-family range (180-1,830) that is
itself downstream of two compounding Guessing-tier figures (adoption
rate, conversion rate — Market & Competition) and an unresolved
child-to-family unit-conversion gap (Market & Competition, named residual
gap this cycle). The revenue range is wide enough (roughly 10×,
low-to-high) to be of limited planning value.

**Opportunities.** Zero paid acquisition genuinely removes one cost
variable from an already tight budget, and the subscription price
undercuts the one directly comparable local competitor on an
annualized basis (Opportunity: R719.88/family/year vs. MoneyTime SA's
R995/year).

**Missing Information.** Curriculum content-production cost (Revenue &
Costs, "Still open"); post-runway funding-ask size (Financial
Considerations); a magnitude for the self-fund-further commitment;
break-even analysis of any kind — none exist anywhere in the case.

**Recommendations.** Put at least a directional ceiling on the
self-fund-further commitment (e.g., a stated maximum number of months or
a stated maximum personal-capital figure) — an unbounded personal
commitment is not a plan a financial reviewer can evaluate or rely on.

**Confidence Level:** Low, specifically on the financial-sizing
questions; Medium on the qualitative resourcing logic.

**Support Recommendation:** Gather More Information (specifically: a
costed self-fund ceiling, a curriculum-production cost estimate, and a
post-runway funding-ask size).

---

### Expert 6: South African Consumer Market Analyst

**Assessment.** Market & Competition is, following this cycle's restored
detail, the most thoroughly documented section in the case — population
base, device access, OS split, parent digital-financial engagement, a
full funnel derivation, three named local competitors, and international
comparables are all present with explicit evidence tiers.

**Strengths.** The competitive positioning is genuinely differentiated
(payroll-simulation mechanic vs. debit-card-for-kids), and this is
supported by naming exactly what each of three local competitors is
missing (Market & Competition) rather than asserting differentiation
without comparison.

**Weaknesses.** The two most decision-relevant figures in the entire
funnel — Year-1 adoption capture (0.3-1%) and freemium-to-paid conversion
(1-3%) — are both explicitly the user's own "least-evidenced,"
Guessing-tier estimates, inferred from non-South-African markets (Market
& Competition). Every revenue figure in the case is downstream of these
two numbers.

**Risks.** Organic-only acquisition (decided this cycle) is being
applied against an 18,000-61,000 family-install target with "no
validation plan of any kind anywhere in the case" (Validation Strategy)
and no South African benchmark for whether organic discovery alone can
plausibly reach that range (Outstanding Questions, Critical Gap #4). At
the same time, the one channel with local, demonstrated reach precedent
— schools partnerships, per MoneyTime SA's self-reported 1,500 schools
and 130,000 students (Market & Competition) — remains completely
unscoped: "no timeline, target, or resourcing plan" (Opportunity, Market
& Competition, Outstanding Questions). Locking acquisition strategy to
organic-only before even lightly scoping the one channel with local
precedent is a sequencing risk.

**Opportunities.** The schools-partnership channel could be scoped at
near-zero cost (a handful of exploratory outreach conversations) without
requiring the paid-acquisition budget the founder has correctly decided
to avoid.

**Missing Information.** MoneyAfrica Kids' premium price remains unknown
(Market & Competition); no South Africa-specific comparable exists for
FamZoo/Bomad-style track-only products, meaning willingness-to-pay
remains unvalidated locally in every direction.

**Recommendations.** Scope the schools-partnership channel at a
lightweight, exploratory level before treating organic-only as the
final, sole acquisition strategy for the full 6-12 month growth horizon.

**Confidence Level:** Medium on competitive positioning; Low on demand
and conversion figures.

**Support Recommendation:** Proceed with Changes.

---

## Panel Discussion

**Consensus.** All six experts agree the legal/regulatory foundation
(Legal & Compliance, Child Data & Consent) is the case's strongest, most
genuinely specialist-reviewed component, and that the document is
unusually candid about naming its own gaps rather than concealing them.
All six also independently converged, from different angles, on the same
structural pattern: several items reported as "resolved this cycle" are
resolved only in the sense that a *decision to decide later, or to
proceed without full review, was made* — not that the underlying
uncertainty was closed. This applies to the self-fund contingency
(uncosted), the motivation-probe and data-breach commitment (both
Incubator-drafted, unreviewed), and curriculum authorship (explicitly
open).

**Disagreements.** The Financial Analyst frames the self-fund-further
gap as severe enough to warrant "Gather More Information" outright; the
Regulatory Counsel and Market Analyst are more willing to accept
"Proceed with Changes" because the legal and competitive fundamentals are
sound enough to build on while the financial gap is closed in parallel.
The Child Development and Data Privacy specialists disagree with the
document's own sequencing (Roadmap places their specialist reviews
"during build phase" or "before pilot enrollment" as advisable, not
mandatory) — both would block pilot enrollment specifically, not just
flag it as a recommendation.

**Trade-offs.** Requiring all specialist reviews and a costed
contingency before proceeding further slows an already tight 6-month
runway further — but proceeding without them risks running a pilot on
unreviewed, child-facing psychological instruments and an unreviewed
children's-data breach protocol, which is a materially different (and
harder to reverse) kind of risk than a schedule slip.

**Alternative approaches.** A staged approach was discussed: allow build
and legal-recheck work to proceed immediately (low incremental risk),
while treating specialist review of the motivation-probe and
data-breach commitment, a costed self-fund ceiling, and a curriculum
authorship decision as hard gates specifically before pilot enrollment
begins — rather than blocking all forward motion. This reflects most of
the panel's Proceed with Changes stance rather than a full stop.

**Remaining uncertainties.** Whether the zero-marginal-cost advice policy
genuinely extends to instructional design and data-privacy practitioner
time (repeatedly flagged as "undocumented" across multiple sections) is
itself unresolved and affects the feasibility of several other
recommendations above.

---

## Investment Committee's Own Devil's Advocate

Built fresh from this panel's own reasoning, not inherited from any
Incubator artifact:

1. **The Readiness Score's "no margin" claim is not robust to the
   document's own logic.** Constraints is scored Complete (Readiness
   Score table) in part on the strength of the self-fund-further
   decision. But per the Readiness Score section's own stated rule —
   "documentation of an open decision is not resolution of it" — an
   uncosted, undated, unbounded personal commitment is arguably exactly
   that: documentation of an intention, not a resolved constraint. If
   Constraints were scored Partial under the section's own stated
   standard, the score drops from 91 to 88 (67.7%), below the 70%
   completion-gate threshold the document claims to clear "with no
   margin." The Business Case's own Self-Certification section does not
   address this internal tension at all.

2. **Two "resolved" required changes were resolved by generating content,
   not by obtaining the expertise the content requires.** The motivation-
   probe and data-breach commitment were each drafted by the Incubator
   itself, specifically to close a prior Investment Committee required
   change — and the document is explicit that neither has been reviewed
   by the specialist whose domain it falls in. Closing an Investment
   Committee item by producing unreviewed placeholder content, rather
   than by obtaining the review the item actually called for, closes the
   item on paper without closing the underlying risk it was meant to
   address.

3. **The acquisition strategy was decided before the one channel with
   local proof-of-concept was even scoped.** Organic-only was adopted as
   "decided" (Revenue & Costs, Constraints) in the same cycle that Market
   & Competition confirms MoneyTime SA — the closest local analog —
   built its reach entirely through schools, not organic discovery. No
   organic-only South African comparable exists anywhere in the case's
   own research. This is a decision made in the absence of, not in light
   of, the most relevant available evidence.

4. **The pilot is being asked to do more work than its own design
   premise supports.** The pilot is explicitly "directional and
   qualitative" per the child-development reviewer's own underpowering
   caution (Problem, Validation Strategy) — yet it is simultaneously
   relied upon as: the demand signal, the mechanic-safety signal, the
   family-stress early-warning signal, and now the motivation-crowding-
   out signal. A single 20-50-family, non-statistically-powered pilot is
   carrying four distinct validation burdens at once, several of which
   (family stress, motivation crowding-out) concern welfare-relevant
   outcomes for children, not merely product-market fit.

---

*End of Full Review. See `Verdict_v5.md` for the outcome, Gate Integrity
Check, and Risks and Assumptions register.*
