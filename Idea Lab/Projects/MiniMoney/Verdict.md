# Investment Committee Verdict: MiniMoney — v8

## Verdict: Sufficient context — Proceed with changes

The Business Case (`BusinessCase_v8.md`) contains enough detail —
operational mechanics, a resolved monetization decision, a first
primary-research data point, and an explicit, reasoned articulation of
its own open questions — for this Committee to form a substantive
judgment rather than declare the record insufficient. The case should
not proceed unmodified to the Developing Committee, however. It should
return to the Incubator with the following required changes, all cited
to specific Business Case sections, before re-entering Investment
Committee review:

1. **Legal & Compliance sequencing must be tightened, not merely
   disclosed.** The specialist POPIA/ARB opinion may remain deferred to
   the build-spec stage as the user has chosen (Legal & Compliance), but
   the execution plan must include a firm trigger/deadline for
   commissioning it, and must explicitly gate the invoice/payment-
   trigger/late-penalty/data-retention features specifically — not the
   whole build — behind that opinion being obtained. Foundational,
   non-financial rails (UI shell, task engine, curriculum content) may
   proceed in parallel. A short, low-cost preliminary legal read on the
   two highest-stakes questions (money-transmitter characterization;
   "payslip"/"invoice"/"late penalty" terminology risk to minors) before
   any further version, rather than waiting for the full opinion, should
   be considered.

2. **A subscription price point must be set**, even as a stated range
   with rationale, before Financial Considerations or Revenue & Costs
   can be treated as modelable (Value Proposition, Business Model,
   Financial Considerations currently rely solely on MoneyTime SA's
   R995/year, explicitly flagged as an under-anchor).

3. **The 90-day (15,000) vs. annual funnel (18,000-61,000) target
   tension must be resolved, not described.** The case must state
   explicitly whether a front-loaded launch-marketing push is assumed
   (and what it is), or revise the 90-day target to track the funnel's
   low end (Objectives, Risks).

4. **The 3-month, solopreneur, AI-assisted build timeline must be
   reconciled against the cited $25,000-$120,000+ engineering-cost range**
   sourced from five agency estimates (Revenue & Costs, Constraints) — as
   written, these two figures sit unreconciled in the same document.

5. **The late-penalty mechanic (5→6→7 Mbucks/week) requires an explicit
   child-development/age-appropriateness review**, distinct from its
   current framing purely as a trust/enforcement/dispute risk
   (Operations, Success Criteria, Risks). At minimum, the planned 20-50
   family pilot's success criteria should be expanded to track family-
   relationship strain by child age band, not only completion rates.

6. **The n=10 interview data's sampling method, recruitment channel, and
   question wording should be documented**, or the data point should be
   explicitly bounded in future versions to prevent it from acquiring
   more evidentiary weight than an undocumented convenience sample of 10
   families warrants (Problem, Supporting Evidence).

None of these six items is individually disqualifying, and none
requires abandoning the venture. Together, they represent the specific,
correctable gap between where this case currently stands and a case this
Committee could support proceeding to execution planning.

---

## Mandatory Gate Integrity Check

This Committee was given only `ExecutiveSummary.md` and
`BusinessCase_v8.md` — not `ExpertRoster.md` or
`reviews/DevilsAdvocate.md` — and did not read them, per its mandated
isolation. The following assessment is therefore based only on how the
Business Case itself describes and references those self-certified
items, not on their actual content.

**Readiness Score self-certification: holds up, and is notably NOT
superficial.** The Business Case's own Self-Certification Against
Completion Gate section (`BusinessCase_v8.md`) states plainly that the
Readiness Score (47%, 61/130) fails the required 70% threshold, and
concludes in its own words: "This Business Case does not currently pass
its own completion gate." This is a transparent, substantive admission
of failure, not a checkbox exercise dressed up as a pass. This Committee
credits the Incubator for this candor and does not flag it as
superficial.

**Expert Roster rationale and Devil's Advocate objections: cannot be
verified from this vantage, and that limitation should be named
explicitly rather than silently assumed away.** The Business Case
references both only by pointer ("see ExpertRoster.md," "see
reviews/DevilsAdvocate.md") with no substantive content reproduced
inline. This Committee has no way to independently confirm whether those
documents' roster rationale (≥3 sentences per entry, naming a specific
case-study assumption) or Devil's Advocate objections (≥3, each citing a
specific section) are substantively done versus superficially present,
because it was deliberately not given access to them. This is not
evidence of a problem — it is a structural limitation of this review's
isolation design — but it should not be silently treated as "verified."
The Developing Committee, or a future audit, should confirm these two
items directly against their actual content, not rely on this
Committee's inability to check them as tacit clearance.

**One process observation for the Chief of Staff, not a Gate Integrity
finding against the Incubator's work itself:** per the Idea Lab routing
rules, an Incubator gate failing the Readiness Score threshold should
have triggered a manual user gate-check before delegation to this
Committee, rather than (or in addition to) proceeding straight to
Investment Committee review. This Committee proceeded with its review
regardless, since its mandate is to assess the Business Case as
delivered, not to police the routing sequence that delivered it — but
this sequencing point is worth the Chief of Staff's attention
independent of this case's substantive verdict.

---

## Risks and Assumptions

The following items were flagged during this review and must be traced
by the Developing Committee — none may be silently dropped downstream:

- **Regulatory/legal:** No specialist POPIA/ARB legal opinion has ever
  been obtained (Legal & Compliance). The deferral to build-spec stage
  is a conscious user decision but does not reduce the underlying,
  untested risk that the invoice/payment-trigger/late-penalty/
  terminology mechanics could be characterized as money-transmission-
  adjacent or otherwise regulated. No ARB/NCR precedent exists for
  "payslip"/"invoice"/"late penalty" terminology applied to minors.

- **Child data / risk-accepted assumptions:** Two specific compliance
  questions (POPIA Section 14 retention sufficiency; exam-bonus
  mechanic's schools-data-privacy status) are explicit, standing user
  risk acceptances, unverified by any external authority (Legal &
  Compliance, Child Data & Consent extension).

- **App-store platform risk:** Apple's Kids Category IAP-currency rule
  as applied to Mpoints remains unresolved (Medium confidence); Apple's
  Kids Category age bands (topping at 9-11) appear structurally
  incompatible with MiniMoney's 6-18 span for any future iOS port
  (Business Model, Technology, Child Data & Consent extension).

- **Evidence quality:** The case's only primary, MiniMoney-specific
  research is n=10 family interviews with undocumented sampling method,
  recruitment channel, and question wording (Problem, Supporting
  Evidence) — directional only, not validated demand.

- **Pricing/financial modeling:** No subscription price point exists;
  MoneyTime SA's R995/year is flagged as a likely under-anchor (Value
  Proposition, Business Model). No numeric budget, runway, or funding ask
  exists anywhere in the case (Financial Considerations).

- **Target/planning consistency:** The 15,000-in-90-days download target
  is only cleanly consistent with the upper half of the annual funnel
  range (18,000-61,000); no front-loaded marketing assumption is stated
  anywhere to justify it (Objectives, Risks).

- **Execution capacity:** A solopreneur, AI-assisted, ~3-month
  directional build timeline (Constraints) is unreconciled against the
  case's own cited $25,000-$120,000+ agency engineering-cost estimates
  (Revenue & Costs).

- **Human/psychological risk:** The escalating late-penalty mechanic
  (5→6→7 Mbucks/week, pilot cap 3, honor-system enforced) has never been
  evaluated from a child-development/age-appropriateness standpoint in
  any version of this case — only through a trust/enforcement/dispute
  lens (Operations, Success Criteria, Risks).

- **Distribution dependency:** The schools-partnership channel — the
  strongest locally-demonstrated reach signal available (MoneyTime SA's
  130,000-student reach) — has no stated timeline, target school count,
  or resourcing plan (Opportunity, Outstanding Questions).

- **Self-certification visibility gap:** This Committee could not verify
  the substantive content of `ExpertRoster.md` or
  `reviews/DevilsAdvocate.md` from its permitted inputs; this is a
  structural limitation, not a finding, but the Developing Committee or a
  later audit should confirm these directly.
