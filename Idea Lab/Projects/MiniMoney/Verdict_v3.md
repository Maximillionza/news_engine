# Investment Committee Verdict: MiniMoney (v17 cycle)

## Outcome: Sufficient context — Proceed with Changes

**The case.** MiniMoney's two multi-cycle Critical-section blockers —
money-transmitter/payment-facilitation risk and child-data/consent
sufficiency — are now genuinely resolved via credible, Verified-tier
retained-professional opinions (`BusinessCase_v17.md`, *Legal &
Compliance*; *Legal & Compliance — Child Data & Consent*), not asserted
away. No Critical section is Incomplete, and the Readiness Score (70%,
91/130) clears the completion gate's threshold for the first time in this
case's history (*Readiness Score*). This is a substantive, not
cosmetic, development: the specialist opinions resolved genuinely hard
questions (money-transmitter characterization, minor contractual
capacity) largely in the business's favor while also surfacing real new
risk (SARB/NPS Act, FPB, family-stress residual risk, exam-bonus design
flaw) rather than uniformly validating the design — the hallmark of
substantive, not superficial, expert engagement.

However, the case should not advance to Developing Committee unmodified.
Six named, specialist-recommended design decisions remain undecided;
two newly-surfaced regulatory questions (one of which — FPB
classification of Mpoints — affects a core mechanic, not a peripheral
feature) have no owner or date; financial and market-demand gaps persist
unchanged across two versions; and the product's core educational
content (curriculum) does not yet exist behind its own recommended
framework. These are not foundational "insufficient context" gaps of the
kind that gated this case since v9 — they are scoped, actionable items —
but they should be resolved, and the Business Case updated to reflect the
resolution, before execution planning begins.

### Required changes

1. **Decide and document all six named-but-unadopted specialist design
   recommendations** before this case advances further: (a)
   parent-facing-only debt terminology; (b) exam-bonus redesign
   (behavior- vs. outcome-contingent); (c) late-penalty mitigation path
   (grace-period mechanism vs. pilot-measurement-only); (d) Fintech
   Advance gamification-avoidance; (e) three-tier curriculum content
   design direction; (f) formal adoption of the pilot-measurement
   package into pilot design. Per this Committee's own panel discussion,
   items (b) and (c) specifically should be resolved before any real
   family is enrolled in the pilot — not merely before Developing
   Committee handoff.
2. **Reconcile the subscriber-count discrepancy** (180-1,830 vs.
   360-2,440) and the **family-vs-child install ambiguity**, both
   unresolved unchanged since v16 (*Revenue & Costs*; *Financial
   Considerations*; *Market & Competition*).
3. **Assign a named owner and target date** to both pre-build regulatory
   rechecks (SARB/NPS Act for account-linking; FPB applicability
   assessment for Mpoints), and decide explicitly whether launch proceeds
   without account-linking and/or without the current Mpoints mechanic
   if either recheck is unresolved by the build date. Treat the FPB
   question with higher urgency than the account-linking question — it
   touches the core gamification loop, not an optional feature.
4. **Verify the one legal-opinion case citation** flagged by the retained
   expert as unverified, before any public or filed use (*Legal &
   Compliance*, Q4).
5. **Commit to a curriculum-content workstream** (authorship,
   instructional format, standards alignment) running in parallel with,
   not after, the engineering build — the three-tier framework currently
   has zero instructional content behind it (*Curriculum Design*).
6. **Decide explicitly what the 20-50 family pilot validates** — mechanic
   safety/child-development signal only, or also demand — and design
   recruitment accordingly, given no other market-demand study is
   currently scheduled (*Validation Strategy*; *Problem*).
7. **Produce at least a rough cost/runway estimate**, given the venture
   is solopreneur-resourced with external help engaged only on-demand
   and currently carries no funding ask, runway, or financial projections
   at all (*Financial Considerations*; *Constraints*).

---

## Mandatory Gate Integrity Check

This Committee did **not** read `ExpertRoster.md` or
`reviews/DevilsAdvocate.md` — per its isolation mandate, it was given
access only to `ExecutiveSummary.md` and `BusinessCase_v17.md`, and did
not open any other file present in the case folder even though some may
exist on disk. **This Committee therefore cannot directly confirm or
deny whether the Incubator's self-certified expert-roster rationale or
Devil's Advocate objections are substantively done versus superficially
present** — that determination would require reading files this
Committee is structurally barred from opening, and no inference from the
Business Case alone can substitute for direct inspection of those files.

What **is** visible, and worth flagging as a related but distinct
integrity concern found within `BusinessCase_v17.md` itself: several
sections are marked **Complete** while their own text explicitly
acknowledges multiple named, unadopted mitigations or pending decisions —
*Operations* is Complete despite three recommended design changes "not
yet adopted"; *Risks* is Complete while stating outright that
"comprehensive identification... does not mean the risks are
eliminated"; *Roadmap* is Complete while listing numerous pre-pilot
decisions still pending. This suggests the case's own scoring rubric may
use "Complete" to mean "identified and documented" rather than
"resolved," which the ≥70% Readiness Score threshold does not itself
distinguish. This is not evidence of bad faith — the document is
consistently transparent about which items are pending within each
Complete-marked section — but the Developing Committee should not read
"Complete" as "nothing left to decide" without checking each section's
own qualifying text, and the Chief of Staff may wish to confirm with the
Incubator whether "Complete" is intended to mean "fully specified and
documented" (regardless of whether recommendations have been acted on)
or "resolved with no open decisions," since the two readings currently
coexist in the same document.

**Conclusion: self-certification of the completion-gate checklist itself
(Status/Confidence/Evidence tagging, no Critical+Incomplete section,
Readiness Score ≥70%, no orphaned "unchanged, not reproduced" section)
holds up under review — each claim in `BusinessCase_v17.md`'s
Self-Certification section is independently verifiable from the document
itself and checks out.** The two items requiring roster/Devil's-Advocate
file inspection (expert roster entries ≥3 sentences each; Devil's
Advocate objections ≥3, each citing a specific section) are outside this
Committee's readable scope and are explicitly flagged above as
**unverified by this Committee**, not confirmed.

---

## Risks and Assumptions (for the Developing Committee to trace)

- Mbucks non-transferability is a load-bearing legal assumption
  underpinning the entire low-money-transmitter-risk finding; any future
  roadmap feature must be checked against it before build, or the
  underlying legal analysis must be redone (*Legal & Compliance*, Q1;
  *Constraints*).
- SARB/National Payment System Act open-banking status is genuinely
  unsettled (draft regulation, not finalized) and gates the
  account-linking feature (*Legal & Compliance*, Q6; *Roadmap*).
- FPB classification of Mpoints is uncertain and fact-specific, and — per
  this Committee's own assessment, contrary to the case's equal-weighting
  of it alongside the SARB question — potentially affects the product's
  core mechanic, not a peripheral feature (*Legal & Compliance*, Q7).
- One legal-opinion case citation is flagged by the retained expert as
  unverified, pending a pinpoint-reference check (*Legal & Compliance*,
  Q4).
- ARB Clause 6.1 (financial-product advertising) and Clause 14.2
  (children's advertising) both apply; named as the single
  highest-optics-risk item in the case; mitigation (parent-facing-only
  terminology) is identified but not built (*Legal & Compliance*, Q5;
  *Risks*).
- POPIA Section 14 retention period and deletion trigger are not yet
  designed — confirmed as a required, affirmative design task, not a
  closed legal question (*Legal & Compliance*, Q3; *Roadmap*).
- The recommended lightweight parent identity-verification step is not
  yet built (*Legal & Compliance*, Q2).
- The Family Stress Model's affective pathway (parental stress →
  child wellbeing) is confirmed to persist even under the child-invisible
  late-penalty redesign; risk is narrowed, not eliminated; two named
  mitigation paths remain undecided (*Success Criteria*; *Risks*;
  *Operations*).
- The exam-performance bonus mechanic is confirmed, on cited evidence, to
  be a design specifically likely to crowd out intrinsic motivation, and
  remains the build-of-record pending an undecided redesign (*Operations*;
  *Assumptions*; *Outstanding Questions*).
- The Fintech Advance module's "no real trading" safeguard addresses
  financial-loss risk but not the reviewer-identified risk of
  normalizing a relationship to speculative risk-taking via familiar
  gamified mechanics; mitigation not yet adopted (*Value Proposition*;
  *Risks*).
- The planned 20-50 family pilot is explicitly underpowered for
  full statistical validation per the reviewer's own caution — intended
  for qualitative early-warning signal only (*Success Criteria*).
- The n=10 first-party interview data point is explicitly non-
  representative; a standing instruction since v9 forbids treating it as
  a validated demand signal (*Problem*).
- Curriculum-engagement (30%) and operational-health (65%) success
  benchmarks carry no external benchmark and should be treated as
  placeholders, not evidence-grounded targets (*Success Criteria*).
- The subscriber-count discrepancy (180-1,830 vs. 360-2,440) and the
  family-vs-child install ambiguity remain unresolved, unchanged since
  v16 (*Revenue & Costs*; *Financial Considerations*; *Market &
  Competition*).
- No funding ask, runway, or full financial projections exist for a
  solopreneur, AI-assisted-development venture with external help
  engaged only on-demand (*Financial Considerations*; *Constraints*).
- Curriculum instructional format, standards alignment, and content
  authorship are entirely unspecified beyond the new three-tier age
  framework, which is itself not yet reconciled with the product's
  existing six-way stakeholder sub-bands (*Curriculum Design*).
- Technology remains unspecified in three concrete respects: how
  account-linking is technically initiated, how payment confirmation is
  captured beyond the accept/dispute UI, and the exam-bonus grade-input
  mechanism (*Technology*).
- Dispute-escalation beyond the 48-hour window has no formal resolution
  mechanism (*Risks*; *Outstanding Questions*).
- Google Play Families Policy loyalty-point disclosure and Apple Kids
  Category IAP-currency questions remain open platform-policy items,
  distinct from the statutory FPB question (*Legal & Compliance — Child
  Data & Consent*).
- The schools-partnership distribution channel, independently flagged as
  the strongest demonstrated reach model in the category, has no
  timeline, target, or resourcing plan (*Opportunity*; *Outstanding
  Questions*).
- iOS porting remains deferred; Android-only at launch (*Constraints*;
  *Target Users/Customers*).
- This Committee could not verify the Incubator's self-certified expert
  roster or Devil's Advocate items directly (see Gate Integrity Check
  above) — this is a scope limitation of this review, not a finding
  either way, and should not be treated as either confirmation or
  refutation by downstream stages.
