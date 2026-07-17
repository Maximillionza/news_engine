# Investment Committee — Verdict: MiniMoney (Business Case v18)

## Verdict

**Sufficient context — Proceed with changes.**

The case (Business Case v18) is thorough, honest about its own
limitations, and has substantively resolved the prior review cycle's
seven required changes through genuine user decisions rather than mere
documentation. The legal, consent, and minor-contractual-capacity
foundations are comparatively strong and Verified-tier (Legal &
Compliance; Legal & Compliance — Child Data & Consent). However, the
case's own top-named Critical Gap — execution capacity — is
under-addressed relative to its stated severity, and several
specialist-identified gaps that are cheap to close remain open. These
must be resolved, at the decision level, before the case proceeds further
(e.g., to Developing Committee). None of the required changes below is a
disqualifying flaw; each is closeable without re-litigating the case's
core design.

**Required changes:**

1. **Name an acquisition/CAC plan, however minimal.** No CAC estimate or
   marketing budget exists against the 18,000-61,000 install funnel
   (Revenue & Costs, "Still open"). At minimum, state an explicit
   decision (even "organic-only, zero paid acquisition, at this
   founder's discretion") rather than leaving the funnel's acquisition
   mechanism entirely unaddressed.
2. **State a runway-slippage contingency and a month-6 decision rule.**
   The case names execution capacity as its binding constraint (Critical
   Gaps §1) but has no stated action for what happens if any one of the
   five-plus concurrent workstreams slips, or if month 6 arrives without
   secured funding (pause, self-fund further, or close).
3. **Instrument the exam-bonus motivation-risk residual before pilot
   enrollment.** The case names a "measurement gap" (Success Criteria)
   between the accepted intrinsic-motivation risk (Operations, decision
   1b) and the adopted pilot instrumentation, which measures family
   stress but not motivation. Add a lightweight qualitative probe
   (parent- and child-facing) at near-zero marginal cost.
4. **Name curriculum authorship explicitly.** No author, format, or
   standards-alignment plan exists (Curriculum Design; Outstanding
   Questions) despite the workstream being committed to start
   immediately, in parallel with the build, competing for the same solo
   founder's time as everything else.
5. **Add a minimal data-breach/incident-response commitment** to
   Constraints or Roadmap before real children's data is collected at
   pilot (no such commitment currently exists anywhere in the case).
6. **Treat Conradie v Rossouw citation verification as a hard,
   non-negotiable gate** before any public or marketing use of the legal
   opinion — already tracked (Critical Gaps §8) but underpins the case's
   self-described "strongest legal position" (Legal & Compliance §4) and
   should be elevated accordingly.

None of these require re-opening the seven changes already resolved this
cycle; all are additive, targeted, and low-cost to close.

---

## Mandatory Gate Integrity Check

The Business Case's own "Self-Certification Against Completion Gate"
section (BusinessCase_v18.md, final section) lists six self-certified
items. Four of the six are substantiated inline, with actual reasoning
reproduced in the document itself (e.g., the Readiness Score
justification, the Critical+Incomplete check, the "no section is a bare
pointer" check — which even names and justifies the one section, Market &
Competition, that required rebuilding this cycle).

**Two items appear satisfied only superficially — technically present,
not substantively demonstrated within what I was permitted to review:**

- **"Expert roster entries ≥3 sentences, each naming a specific
  case-study assumption: see `ExpertRoster.md`, regenerated this
  cycle."** This is a bare external pointer with zero content reproduced
  in the Business Case itself. Unlike its sibling bullets in the same
  self-certification list, there is no in-document evidence (a quoted
  roster entry, a named assumption tied to a named expert) that would let
  a reader independently confirm the claim.
- **"Devil's Advocate objections ≥3, each citing a specific section: see
  `reviews/DevilsAdvocate.md`, regenerated this cycle."** Same pattern:
  asserted by reference only, with no objection content, count, or
  section-citation reproduced anywhere in the Business Case to
  substantiate it.

I want to be precise about what this finding does and does not mean. By
design, I am barred from reading `ExpertRoster.md` and
`reviews/DevilsAdvocate.md` directly — that isolation is the point of my
independence, and I have not attempted to route around it. I therefore
cannot confirm whether the underlying files are actually thin or
actually substantive; the underlying work may well be excellent. What I
*can* observe, from the Business Case alone, is that these two
self-certification bullets are structurally different from their four
siblings in the same list — they are checked off by pointer rather than
demonstrated in place — and that pattern is exactly the kind of
"technically present, not substantively shown" gap this check exists to
surface. I flag it as a presentation/verifiability gap in the
self-certification, not as a confirmed finding that the roster or
Devil's Advocate work is actually weak.

The remaining four self-certified items hold up under review: they are
substantiated with in-document reasoning I could independently trace
against the Business Case's own section content.

---

## Risks and Assumptions

Everything flagged during this review, to be traced by the Developing
Committee — nothing here should be silently dropped downstream:

**Execution/financial:**
- Solo-founder execution across five-plus concurrent workstreams (build,
  curriculum authoring, pilot execution/instrumentation, two regulatory
  rechecks) inside a 6-month runway with a R10,000 total cash budget and
  zero buffer for professional rescue if founder capacity fails
  (Critical Gaps §1; Financial Considerations; Risks).
- No CAC estimate, marketing budget, or acquisition channel plan exists
  against the 18,000-61,000 install funnel (Revenue & Costs).
- No break-even/P&L analysis exists; the R10,000 budget's coherence
  depends entirely on unpaid founder labor plus AI-assisted development
  (Financial Considerations).
- No post-runway funding-ask size or form is stated, and funding will be
  sought at month 6 with only directional (non-statistical) pilot
  evidence as the strongest available proof point (Financial
  Considerations; Roadmap; Critical Gaps §4).
- No stated contingency or decision rule for what happens if the runway
  ends without funding secured.
- The professional-opinion policy (zero marginal cost) has undocumented
  scope/limits — an unverified assumption load-bearing for both the
  budget and the two regulatory rechecks (Assumptions).
- The 6-month runway itself is an untested founder commitment, never
  stress-tested against the case's own five-plus parallel workstreams.

**Regulatory:**
- SARB/National Payment System Act open-banking question remains
  externally unsettled; owner is the user personally, timing is
  build-spec stage, fallback is launch without account-linking (Legal &
  Compliance §6; Critical Gaps §2).
- FPB classification question over Mpoints remains externally unsettled;
  owner is the user personally, fallback is launch without Mpoints, with
  traced ripple effects on the cosmetic store, the 6-9 tier's
  immediate-feedback loop, and the Google Play loyalty-disclosure item
  (Legal & Compliance §7; Critical Gaps §3). The badge-residual
  classifiability question within this recheck is not yet resolved.
- Conradie v Rossouw pinpoint citation remains unverified, and underpins
  the case's self-described strongest legal position (Legal &
  Compliance §4; Critical Gaps §8).
- No ARB ruling addresses this product's fact pattern; MiniMoney could be
  a "natural first test case if challenged" (Legal & Compliance §5), with
  no named legal-defense budget or complaint-response plan.
- Non-account-linking parent identity-verification route (needed if the
  SARB fallback triggers) is named but not yet designed (Legal &
  Compliance §6; Roadmap).
- No data-breach/incident-response commitment exists anywhere in the
  case despite real children's data collection beginning at pilot.

**Child development/psychology:**
- The exam-bonus hybrid retains an outcome-contingent bonus layer against
  the specialist-cited Deci, Koestner & Ryan (1999) crowding-out
  evidence; this residual risk is accepted but not instrumented in the
  adopted pilot measurement package, which targets family stress, not
  motivation (Operations; Success Criteria; Risks).
- The Family Stress Model's affective pathway from the late-penalty
  mechanic is narrowed (grace-period/pre-escalation mechanism, decision
  1c) but explicitly not eliminated (Success Criteria; Risks).
- The three-tier curriculum age framework's reconciliation with the
  product's existing six-way stakeholder sub-bands (6, 7, 8, 9-10, 11-14,
  15-18) is still not done, despite being flagged in a prior review cycle
  (Curriculum Design; Critical Gaps §6).

**Market/demand:**
- Market demand remains directionally evidenced only: the n=10 interview
  round is non-representative (governed by a standing instruction), and
  the 20-50 family pilot is explicitly acknowledged as statistically
  underpowered for demand validation (Problem; Validation Strategy;
  Critical Gaps §4).
- No structured market-sizing study exists anywhere in the plan (Market &
  Competition).
- The schools-partnership channel — named as the strongest demonstrated
  reach model in the category — has no timeline, target, or resourcing
  plan (Market & Competition; Roadmap).
- MoneyAfrica Kids' premium price remains unpublished/unknown (Market &
  Competition).
- Success-criteria benchmarks (curriculum engagement 30%, operational
  health 65%) carry no external benchmark; retention has no proposed
  figure at all (Success Criteria; Critical Gaps §5).

**Product/content:**
- Curriculum content does not yet exist; no named author, instructional
  format, or standards-alignment plan (Curriculum Design; Outstanding
  Questions; Critical Gaps §6).
- Dispute-escalation beyond the 48-hour window has no formal resolution
  mechanism (Operations; Outstanding Questions).
- The "request for payment" prompt feature's coherence under the
  child-invisible late-penalty model remains an open design question
  (Outstanding Questions).
- Average children-per-family distribution within the up-to-4 cap is
  unknown, affecting usage-load and curriculum-exposure modeling
  (Assumptions).
- iOS port timing is undecided, gated on Android traction (Objectives;
  Roadmap).

**Methodology/process risk (for the Developing Committee's own use):**
- The Readiness Score's "Complete" status, under this cycle's own
  redefinition, means a material decision was made — not that the
  underlying deliverable exists or has been de-risked. Several
  Complete-scored sections (Operations, Risks, Roadmap, Constraints) rest
  on decisions whose substance (curriculum content, motivation-risk
  instrumentation, non-linking identity verification, breach response)
  is not yet built. The Developing Committee should not treat a
  Complete-scored section as build-ready without separately checking
  whether its underlying deliverable actually exists.
- The self-certification gate-integrity observation above (roster and
  Devil's Advocate items being pointer-only in the Business Case's own
  self-certification section) should be independently verifiable at a
  later stage by any body with legitimate access to those files.
