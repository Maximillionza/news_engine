# Investment Committee — Full Review: MiniMoney (v23)

> Reviewed against: `ExecutiveSummary.md` (Pass 1) and `BusinessCase_v23.md`
> (Pass 2). No other case-folder files were read. This review is
> independent of any prior Investment Committee cycle referenced inside
> the Business Case (e.g. `Verdict_v6.md`) — this panel has no memory of,
> and did not consult, that or any other prior verdict. Conclusions below
> are formed fresh from the two authorized inputs only.

---

## Pass 1 — High-Level Review (ExecutiveSummary.md only)

### Provisional Panel Assembled

Based solely on what the Executive Summary reveals about the domain — a
real-money-pegged financial-mechanic app for children/teens (6-18) in
South Africa, subscription-funded, solopreneur-executed — this panel was
assembled fresh:

1. **FinTech/Payments Regulatory Specialist (South Africa)** — the
   product touches money-transmission-adjacent territory (Mbucks pegged
   to Rand, invoicing, payment confirmation, optional account-linking),
   requiring SARB/NPS Act and general e-money-adjacent regulatory
   literacy.
2. **Child Data Privacy Specialist (POPIA / minor consent)** — the
   product collects and processes real children's data and financial
   activity; a data-breach/incident-response commitment is explicitly
   referenced as pending specialist review.
3. **Child Development / Motivational Psychology Specialist** — the
   mechanic uses real-money rewards and penalties (including an
   exam-linked bonus) on minors as young as 6; the Executive Summary
   itself flags an outstanding "exam-bonus motivation-probe" review.
4. **Financial / Unit-Economics Analyst** — subscription pricing, a
   quantified but wide revenue range, and a bounded self-funding
   contingency are all central to viability.
5. **Legal Counsel — Contract & Consumer Protection (Minors)** — the
   product enters into task/reward/payment arrangements with minors,
   raising contractual-capacity and consumer-protection questions.
6. **Growth / Go-to-Market Strategist** — the Executive Summary states an
   organic-only, zero-marketing-budget acquisition strategy against a
   named install/conversion funnel and a defined pilot kill-metric.

### Provisional View

**Genuinely uncertain, leaning cautiously toward Proceed-with-Changes.**
The Executive Summary reads as unusually mature and self-aware for a
document of this type — it names its own evidence tiers (Verified /
Supported / Assumed / Guessing), states an explicit Readiness Score
against a stated threshold, and discloses rather than buries its open
items (two pending specialist reviews, two unsettled regulatory
questions, a wide and Guessing-tier revenue range, an unresolved P&L
gap). That transparency is itself a positive signal. But several items
named in the Executive Summary look, on their face, like they could be
load-bearing rather than cosmetic: two "hard pre-pilot" specialist
reviews that have "not occurred as of this revision" despite apparently
being process-only and low-cost to obtain; a funding fallback that is
"resolved" only in the sense of being named, not in the sense of being
confirmed obtainable; and a revenue funnel still resting on
Guessing/Assumed-tier assumptions after many stated revision cycles.

### What Pass 2 Needs to Confirm or Overturn

- Whether the sections marked "Complete" in the Readiness Score genuinely
  satisfy the document's own stated Complete standard, or whether that
  standard (a made decision, a trigger, an owner, and a fallback all
  count as equivalent to resolution) is being used to launder unresolved
  substance into a passing score.
- Whether the two outstanding specialist reviews (data-privacy;
  child-development motivation-probe) are genuinely gated by a real
  precondition ("once a stable working model exists") or have simply not
  been prioritized despite being available at zero marginal cost.
- Whether the absence of any P&L/break-even analysis is a minor gap or a
  disqualifying one, given the venture is asking for investment-committee
  sign-off.
- Whether the organic-only acquisition thesis has any validation
  mechanism beyond a pilot that the document itself admits only tests
  engagement, not acquisition-volume feasibility.
- Whether the regulatory and legal analysis is as solid as the Executive
  Summary's confident tone ("Verified," case-law citations) suggests once
  read in full.

---

## Pass 2 — Full Review (BusinessCase_v23.md)

### Expert 1 — FinTech/Payments Regulatory Specialist (South Africa)

**Assessment.** Money-transmitter/e-money risk is characterized as low,
contingent on Mbucks remaining a pure, non-transferable, non-redeemable
unit of account (Legal & Compliance Q1; Value Proposition; Business
Model). Two narrower regulatory questions remain open: SARB/NPS Act
open-banking treatment of optional account-linking, and FPB
classification of the Mpoints gamified-rewards system (Legal &
Compliance Q6-Q7; Business Model; Stakeholders).

**Strengths.** The legal reasoning cites specific, relevant authority
(SARB's e-money Position Paper; *Maize Board v Jackson* 2005 (6) SA 592
(SCA) on substance-over-form; NCR's Payment Distribution Agent category
confirmed inapplicable) rather than asserting conclusions unsupported.
Both open questions carry a named owner (the user) and a decided,
launch-viable fallback (launch without account-linking; launch without
Mpoints) — Legal & Compliance, Business Model, Constraints.

**Weaknesses.** The FPB question is explicitly conceded as an
interpretive gap: "no ARB ruling directly addresses this fact pattern" —
Legal & Compliance Q5/Q7. A fallback exists, but invoking it "thins the
subscription tier's child-facing appeal further" (Value Proposition),
meaning the fallback is not commercially free — it is a real product
degradation, understated by being filed as a compliance item rather than
a commercial risk.

**Risks.** Both regulatory rechecks are timed to "build-spec stage" —
i.e., after this Business Case's own sign-off point — with no stated
date or deadline within the 6-month runway (Roadmap). If either recheck
resolves unfavorably late in the runway, the fallback reconfiguration
work is unbudgeted in the R10,000 development budget (Revenue & Costs).

**Opportunities.** The non-custodial, track-only model has structural
precedent (FamZoo, Bomad — Market & Competition) and a genuinely lower
regulatory burden than card-issuing competitors (GoHenry, Greenlight).

**Missing Information.** No stated deadline for the two regulatory
rechecks within the 6-month runway; no described process for deciding
*when* a fallback is invoked versus continuing to wait for resolution.

**Recommendations.** Pull both regulatory recheck target dates forward
into the roadmap explicitly (not just "build-spec stage"), and pre-budget
the fallback-reconfiguration engineering cost, however small, rather than
assuming it is absorbed into the existing R10,000.

**Confidence Level:** Medium-High.

**Support Recommendation:** Proceed with Changes.

---

### Expert 2 — Child Data Privacy Specialist (POPIA / Minor Consent)

**Assessment.** The universal parental-consent gate is assessed as
"legally sufficient as designed" under POPIA s34/s35(1)(a) (Legal &
Compliance Q2; Child Data & Consent extension). POPIA Section 14
retention, however, is explicitly unresolved: "a specific retention
purpose, period, and deletion trigger must be affirmatively designed"
(Legal & Compliance Q3) — a named, still-pending build task (Roadmap;
Critical Gaps item 7).

**Strengths.** A minimal data-breach/incident-response commitment has
been drafted with sensible minimum content — what constitutes a breach,
who is notified (parents, the Information Regulator per POPIA s22),
timeframe, and notification content (Constraints).

**Weaknesses.** That commitment is Incubator-drafted and tagged Evidence:
Assumed — it has not been reviewed by an actual Data-Privacy Practitioner
despite the review being confirmed zero-marginal-cost under the founder's
existing advice policy (Stakeholders; Financial Considerations). The
review's trigger ("once a stable working model exists, and before any
pilot testing with real families begins") is stated as not yet satisfied
as of this, the document's 23rd revision (Executive Summary; Roadmap;
Outstanding Questions; Child Data & Consent extension).

**Risks.** This is a children's real-money, real-data product. An
unreviewed, founder-authored breach-response policy governing real
children's personal information is the single most safety-adjacent gap
in the entire document, and it is explicitly gated to occur before pilot
enrollment — a discipline the document itself asserts ("must not be in
force, and real children's data must not be collected at pilot, until
this review has actually occurred" — Child Data & Consent extension).
The persistence of this gap across many stated revision cycles, despite
zero cost, is itself a signal worth scrutiny (see Devil's Advocate,
below).

**Opportunities.** Because the review is genuinely zero-cost, closing
this gap is not resource-constrained — it is a scheduling/prioritization
decision entirely within the founder's control.

**Missing Information.** No stated target date for "a stable working
model" to exist; no interim technical-safeguard description (encryption
at rest/in transit, access-control model, data minimization) beyond the
policy text itself.

**Recommendations.** Treat this review as a hard pre-condition to any
further pipeline progression toward pilot recruitment, and require
evidence the review has actually occurred — not merely that its trigger
is defined — before this case is considered pilot-ready.

**Confidence Level:** Medium (assessed from the document's own
self-reporting; the underlying draft commitment's technical adequacy is
not independently verifiable from this Business Case alone).

**Support Recommendation:** Gather More Information (the completed
specialist review, specifically) before pilot enrollment — this need not
block the Developing Committee's build-phase work, but must block real
child-data collection.

---

### Expert 3 — Child Development / Motivational Psychology Specialist

**Assessment.** The retained child-development review already shaped
several design decisions: gamification avoidance and risk-literacy
framing for the deferred Fintech Advance module (Value Proposition Q5);
the three-tier age framework (Curriculum Design extension); a
behavior-primary, secondary-outcome-bonus hybrid structure for the
exam-bonus mechanic, intended to reduce (not eliminate) intrinsic-
motivation crowding-out risk (Objectives; Success Criteria; Risks).

**Strengths.** The family-relationship-strain measurement package is
unusually rigorous for MVP-stage instrumentation: validated borrowed
instruments (Parenting Stress Index – Short Form; Family Assessment
Device – General Functioning Scale; an abbreviated Child–Parent
Relationship Scale Conflicts subscale), age-stratified administration,
and within-family/within-week correlation tracking against late-penalty
events (Success Criteria).

**Weaknesses.** The exam-bonus motivation-probe — the instrument meant to
test whether the outcome-contingent bonus crowds out intrinsic motivation
— is Incubator-drafted and not yet specialist-reviewed. The document is
explicit that "the underlying substantive risk remains confirmed, not
resolved" (Success Criteria) and that "no family may be enrolled in the
pilot until this review has actually occurred" (Success Criteria; Risks;
Outstanding Questions) — and it has not occurred as of v23.

**Risks.** The late-penalty mechanic's Family Stress Model affective
pathway is described as "narrowed but not eliminated" (Success Criteria).
Real financial consequences applied to minors as young as 6 carry a
non-trivial risk of household conflict; the mitigation is currently
monitoring-based (an instrument), not design-eliminating.

**Opportunities.** The relationship-strain and motivation-probe
instruments are near-zero marginal cost, piggybacked onto existing survey
events (Success Criteria) — cheap to execute once reviewed.

**Missing Information.** Unlike the commercial acquisition checkpoint
(60% task-cycle completion, explicitly a kill-metric — Success Criteria),
there is no equivalent quantified stop/redesign threshold for the
relationship-strain or motivation-crowding-out instruments. The document
measures these risks but does not state what result would halt or
redesign the pilot.

**Recommendations.** Define an explicit, quantified stop/redesign
threshold for both child-welfare instruments, with the same rigor applied
to the commercial 60% acquisition checkpoint, before pilot enrollment
begins.

**Confidence Level:** Medium — the design process is genuinely
thoughtful, but the two most safety-critical reviews remain unperformed.

**Support Recommendation:** Proceed with Changes (specialist review AND a
quantified stop-criterion, both required pre-pilot conditions).

---

### Expert 4 — Financial / Unit-Economics Analyst

**Assessment.** Revenue is modeled per-family: R59.99/month, up to 4
children, against a Year-1 range of 92-915 paying families
(R5,519-R54,891/month run-rate — Revenue & Costs). The funnel derivation
(≈3.05M reachable families × 0.3-1% Year-1 install capture × 1-3%
conversion) is shown in full (Market & Competition).

**Strengths.** Evidence tiers are applied honestly throughout — Guessing
and Assumed tags are not hidden, and the low-end revenue scenario is
explicitly cross-referenced against the self-fund-further contingency as
a "foreseen, already-planned-for scenario" rather than an unaddressed
failure state (Revenue & Costs; Constraints).

**Weaknesses.** **No P&L or break-even analysis exists anywhere in this
document.** This is not a minor omission — it is named repeatedly by the
document itself as the sole reason Financial Considerations remains
Partial across at least the last three reviewed cycles (Financial
Considerations; Readiness Score; Outstanding Questions). A simple
break-even calculation (fixed costs of R10,000-R20,000 against a per-
family contribution margin at R59.99/month) is a bounded, low-effort,
founder-executable task, not one requiring external research — its
continued absence after this many stated revision cycles is a real
analytical gap.

**Risks.** R10,000 development budget sits 45×-220× below the previously
cited agency-engineering cost comparable ($25,000-$120,000+ — Financial
Considerations), viable only if founder-labor-plus-AI-assisted
development genuinely substitutes for that gap. The self-fund-further
ceiling (R20,000 total) and its named grant fallback are both explicitly
untested for sufficiency and obtainability (Assumptions; Constraints) —
contingent on two unconfirmed founder facts (age; company-registration
status).

**Opportunities.** Even the low end of the revenue range (92 families)
would generate a real, if modest, run-rate (≈R66,229/year); the
annualized subscription price undercuts the one local competitor with
demonstrated reach precedent, MoneyTime SA (Opportunity).

**Missing Information.** Break-even family count; a monthly cash-burn
schedule; sensitivity analysis linking funnel assumptions to runway
timing; the actual application-to-cash timeline for the named grant
candidates (NYDA's ~30 working days is disbursement-after-approval only,
not application-to-cash — Constraints).

**Recommendations.** Require a minimal P&L/break-even model as a
condition of further progression — this is not a research task, it is
arithmetic the founder can produce directly.

**Confidence Level:** Medium — funnel logic is transparent, but the
missing P&L is a hard, unaddressed analytical gap.

**Support Recommendation:** Proceed with Changes (P&L/break-even model
required).

---

### Expert 5 — Legal Counsel, Contract & Consumer Protection (Minors)

**Assessment.** Minor contractual capacity is addressed via the "rights
without obligations" exception, supported by named case law (*Pitout v
North Cape Livestock* 1977; *Conradie v Rossouw* 1919 AD 279 — Legal &
Compliance Q4). Terminology risk (debt-coded language reaching children)
is mitigated by reserving such language to parent-facing surfaces only
(Legal & Compliance Q5; Value Proposition).

**Strengths.** Specific, named case-law citations lend real legal
grounding rather than generic assertion. The rights-without-obligations
structure is a genuinely well-fitted legal foundation for this business
model.

**Weaknesses.** The terminology-risk mitigation rests on reasoned
judgment, not settled authority: "no ARB ruling directly addresses this
fact pattern — a genuine interpretive gap" (Legal & Compliance Q5).
Dispute-escalation beyond 48 hours relies on manual founder review, an
interim placeholder explicitly named as "non-scalable and
founder-capacity-dependent" (Operations; Constraints; Risks), with no
stated volume or capacity threshold at which this placeholder is deemed
to have failed.

**Risks.** A single founder is simultaneously responsible for the build,
an instrumented pilot, two personally-owned regulatory rechecks, and now
also manual adjudication of any dispute unresolved beyond 48 hours — all
inside a 6-month runway (Roadmap; Risks; Operations). No section analyzes
this accumulation as a single aggregate capacity risk; each obligation is
assessed individually.

**Opportunities.** The legal structure itself (rights without
obligations) is a genuine strength relative to competitors relying on
card-issuing/e-money licensing.

**Missing Information.** No stated dispute-volume or founder-bandwidth
threshold that would trigger pausing enrollment or escalating beyond the
manual-review placeholder; no aggregate founder-capacity assessment
across all concurrent pre-launch obligations.

**Recommendations.** Require an aggregate founder-capacity/bandwidth risk
assessment spanning build, pilot, both regulatory rechecks, both
specialist reviews, and dispute adjudication — currently each is treated
as an independent, isolated risk.

**Confidence Level:** Medium-High on the narrow legal questions; Low on
the operational-capacity risk this creates in aggregate.

**Support Recommendation:** Proceed with Changes.

---

### Expert 6 — Growth / Go-to-Market Strategist

**Assessment.** Growth strategy is organic-only, zero paid acquisition,
with the schools-partnership channel — the strongest demonstrated local
reach precedent in the category (MoneyTime SA's claimed 1,500+
schools/130,000+ students — Opportunity; Market & Competition) —
explicitly deferred for stated founder-bandwidth reasons (Constraints).

**Strengths.** The pilot's 60% task-cycle-completion checkpoint is a
genuinely disciplined, quantified kill-metric gating premature scaling
(Success Criteria; Validation Strategy).

**Weaknesses.** That checkpoint validates *engagement*, not *acquisition
volume* — the document concedes this explicitly and repeatedly: it "does
not itself validate whether organic discovery can reach the funnel's
absolute size" (Market & Competition; Risks; Validation Strategy;
Outstanding Questions). This means the single most consequential
commercial assumption underlying the entire revenue range — whether
organic-only, zero-budget acquisition can plausibly reach even the
9,150-family low end of the install funnel — has no validation mechanism
anywhere in the current plan.

**Risks.** Deferring the one channel with demonstrated local reach
precedent while simultaneously betting the entire commercial thesis on
unproven organic-only acquisition is a significant, named-but-unmitigated
strategic tension (Opportunity; Constraints).

**Opportunities.** The n=10 first-party interview shows an encouraging,
if non-representative, directional signal (6/10 willing to pay; 7/10
interested specifically in the education angle — Problem).

**Missing Information.** No breakdown of which specific organic channels
(word-of-mouth, App Store search/organic discovery, social) the founder
actually intends to pursue, or why the 0.3-1% install-capture figure —
sourced from adjacent international markets (GoHenry/Greenlight UK/US) —
should transfer to South African organic-only conditions specifically
(Market & Competition).

**Recommendations.** Require a concrete, even qualitative, named
organic-acquisition channel plan underlying the install-capture
assumption before relying on the funnel for investment-level decisions;
consider a cheap, pre-build empirical test (e.g., a landing-page/waitlist
signal) rather than deferring all acquisition validation to a
20-50-family, founder-network-recruited pilot.

**Confidence Level:** Low-Medium — the funnel math is transparent, but
the acquisition mechanism itself is essentially unspecified.

**Support Recommendation:** Gather More Information (a concrete organic
acquisition channel plan).

---

## Panel Discussion

**Consensus.** The legal foundation (money-transmission risk, minor
contractual capacity) is genuinely solid and grounded in specific,
relevant authority — the strongest part of the case. The document is
unusually transparent about its own evidence tiers and open items rather
than concealing them. That said, the panel broadly agrees that several
sections scored "Complete" in the Readiness Score contain real,
unresolved, safety- or viability-relevant substance: the two pre-pilot
specialist reviews (child-development motivation-probe; data-privacy
breach commitment) remain unperformed despite being zero-cost and
trigger-defined; no P&L/break-even model exists anywhere in the document;
and the single most consequential commercial assumption (organic-only
acquisition reaching the stated funnel) has no validation path.

**Disagreements.** The Financial Analyst and Growth Strategist lean more
skeptical — closer to withholding support outright — because the funnel
and P&L gaps are foundational to the venture's basic viability, not
cosmetic. The Regulatory and Legal experts lean more favorably toward
Proceed with Changes, since the compliance foundation is genuinely strong
and every open regulatory question carries both an owner and a decided
fallback. The Child Development expert sits in between: the design
*process* is rigorous, but the two safety-critical reviews being
performed is a hard, non-negotiable precondition regardless of how well
the surrounding instrumentation is designed.

**Trade-offs.** The document's own operating definition of "Complete" — a
made decision, or a named owner plus trigger plus fallback, counts as
equivalent to resolution — is internally consistent and honestly applied,
but it permits commercially and ethically material uncertainties to be
scored as non-blocking simply because a trigger or fallback has been
named. Naming a trigger is not the same as satisfying it, and the panel
is not confident this distinction is being weighted appropriately in the
score's face value (72.3%/70.0%).

**Alternative approaches.** Consider pulling the schools-partnership
channel back into scope at small scale specifically to empirically test
the one channel with demonstrated local reach, rather than deferring it
entirely on bandwidth grounds. Consider running the two specialist
reviews concurrently with the build phase rather than gating them
strictly behind "a stable working model exists" — since both are
zero-cost, there is no evident reason they could not be initiated in
parallel with build, closing the gap sooner rather than deferring it
further. Consider a cheap, pre-build acquisition signal test (e.g., a
landing page or waitlist) to get an early empirical read on organic
reach before committing the full pilot to a dual-purpose (safety +
demand) design that structurally under-tests the demand side.

**Remaining uncertainties.** The founder's age and MiniMoney's
company-registration/tax-clearance status (both gate the named funding
fallback candidates); the actual outcomes of the SARB/NPS Act and FPB
regulatory rechecks; whether organic-only acquisition can plausibly reach
the stated funnel in absolute terms; whether the exam-bonus/late-penalty
mechanics will produce measurable household stress at pilot scale; and
whether a solo founder can execute build, pilot, two regulatory rechecks,
two specialist reviews, and dispute adjudication inside a 6-month runway
without material slippage in at least one workstream.

---

## Devil's Advocate (Investment Committee's own, built fresh from this panel's reasoning)

The Business Case states it is now on its 23rd revision and references at
least six prior Investment Committee cycles (via its repeated citations
of `Verdict_v6.md`'s "seven required changes"). Look at the pattern of
how those seven required changes were actually resolved: six were
resolved in the prior cycle by defining a trigger, quantifying a
threshold, or naming a fallback *category* — not by completing the
underlying work itself. The seventh was resolved this cycle by hiring a
vendor to produce a prioritized *list* of grant programs the founder may
or may not even be eligible for, contingent on facts (age,
company-registration status) that remain unconfirmed. At what point does
"we have thoroughly documented that we have not yet done X, with an
honest caveat" stop counting as *progress toward doing X*, and start
being recognized as a structural pattern of converting "unresolved" into
"resolved-via-defined-trigger" without ever closing the actual gap?

The document's own scoring rubric explicitly rewards this: a section is
"Complete" when a material question has "a made decision — resolved,
adopted, or a deliberate, documented residual-risk acceptance" (Readiness
Score definition). That definition treats "we have decided how we will
eventually decide this, and who will decide it, and what we'll do if it
goes wrong" as equivalent in scoring weight to actually deciding it. This
is not dishonest — the document is scrupulously clear about the
distinction in its prose — but it does mean the headline 72.3% readiness
figure is doing more rhetorical work than its face value suggests. Ten of
twenty-four scored sections are "Complete" while containing at least one
hard, safety-relevant, zero-cost item that has simply not been done after
many stated cycles (two specialist reviews) or a foundational commercial
assumption with no validation mechanism at all (organic-only acquisition
reaching the funnel).

Press harder on the two specialist reviews specifically: if they are
genuinely zero marginal cost and gated only by "once a stable working
model exists," why, after at least six Investment Committee cycles, does
that working model still not exist? Either the case is being brought to
this Committee prematurely and repeatedly — in which case the underlying
cadence of this review process itself deserves scrutiny — or "stable
working model exists" is functioning as a soft, indefinitely-deferrable
gate rather than a genuinely load-bearing precondition. Either reading
should concern this Committee more than the document's confident,
well-organized tone might suggest at first pass.

Finally: the pilot is explicitly designed to serve "double duty" — both a
mechanic-safety signal and a directional demand read (Roadmap). A
20-50-family pilot, recruited from a founder's own network, on a
zero-paid-acquisition organic-only thesis, is being asked to do double
duty for a *demand and channel-reach* question that the document itself
concedes it cannot answer ("does not itself validate whether organic
discovery can reach the funnel's absolute size"). That is not a paperwork
gap; it is the single largest unresolved commercial risk in the entire
case, and it is scored no more severely than smaller, more clearly bounded
build-spec items like grace-period length.

---

*End of Full Review. See `Verdict_v7.md` for the outcome, Gate Integrity
Check, and Risks and Assumptions register.*
