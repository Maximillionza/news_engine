# Traceability Matrix: MiniMoney

> Prepared by: Developing Committee. Source of every row below:
> `Verdict_v7.md`'s "Risks and Assumptions" section (the section explicitly
> addressed "for the Developing Committee to trace against... Nothing
> below may be silently dropped downstream"), cross-checked against
> `Verdict_v7.md`'s six Required Changes and Gate Integrity Check. Mapped
> against `BusinessCase_v24.md` (final). This matrix is built before
> `PRD.md` and `BuildSpec.md`, per mandate — no row is left with neither
> disposition filled.

## Scope note on the four user-authorized carve-outs

Per the delegation instructions for this cycle, four items named in
`Verdict_v7.md`'s Required Changes (1, 2, 4, 6) were deliberately left
unresolved in `BusinessCase_v24.md`, per an explicit, user-authorized
decision to route directly to the Developing Committee rather than
cycling further through Incubator/Investment Committee rounds. These four
items — (i) completing the two trigger-defined specialist reviews, (ii) a
minimal P&L/break-even model, (iii) a quantified stop/redesign threshold
for the child-welfare pilot instruments, (iv) an aggregate
founder-capacity/bandwidth assessment — are process/compliance/business
obligations, not implementation choices. They are captured below under
disposition **(b)**, with the reasoning stated as "user-authorized
deviation," distinct from other rows also disposed as (b) for different
reasons (see individual rows).

**Hidden-technical-decision check, performed as instructed:** each of the
four was reviewed to confirm none conceals a genuine technical/
architectural decision that the Developing Committee could resolve in its
place.

- Two specialist reviews: a procedural/professional-engagement obligation
  (scheduling and completing external expert review). No technical
  decision hidden.
- P&L/break-even model: founder-executable arithmetic against already-
  stated figures (R10,000 budget, R20,000 ceiling, R59.99/month, 92-915
  paying-family range). No technical decision hidden; nothing here depends
  on an architecture or build choice.
- Quantified stop/redesign threshold for the child-welfare instruments
  (PSI-SF, FAD-GFS, abbreviated CPRS Conflicts subscale, motivation-probe):
  **reviewed specifically for this risk** — setting a clinically meaningful
  threshold on validated psychometric sub-scales requires the same
  child-development clinical expertise the instruments themselves were
  sourced from (`ChildDevelopmentReview_v1.md`), not a generic
  product/engineering judgment call. This is confirmed a domain-expert
  business obligation, not a disguised technical decision — consistent
  with why the Business Case already gates the related motivation-probe
  behind the same specialist's review. Flagged here explicitly, not
  silently resolved.
- Aggregate founder-capacity/bandwidth assessment: a personal,
  self-reported operational-capacity judgment only the founder can make
  about their own concurrent workload. No technical decision hidden.

No red flags found. All four carve-outs stand as genuine non-technical,
outstanding founder actions.

---

## Regulatory / Legal

| # | Verdict_v7.md item | Disposition | Mapping / Reasoning |
|---|---|---|---|
| 1 | SARB/NPS Act open-banking treatment of optional account-linking: unresolved, owned by user, fallback is launch-without-linking, no stated deadline. | (a) Addressed | `BuildSpec.md` §Architecture / §Compliance-as-Constraints: `ACCOUNT_LINKING_ENABLED` feature flag, OFF by default at launch. Owner (founder) and fallback (ship without linking) carried through unchanged from the Business Case; deadline remains "build-spec stage," tracked in `ExecutionInstructions.md` as a pre-launch milestone check, not fabricated here. |
| 2 | FPB classification of Mpoints: unresolved, owned by user, fallback is launch-without-Mpoints, no ARB ruling directly on point. | (a) Addressed | `BuildSpec.md` §Architecture / §Compliance-as-Constraints: `MPOINTS_ENABLED` feature flag, OFF by default at launch; cosmetic store and flat 10-Mpoints-per-task reward removed entirely in that configuration, per Business Case's own decided fallback. Tracked as a pre-launch milestone check in `ExecutionInstructions.md`. |
| 3 | Mbucks non-transferability is a locked, binding product-spec constraint — any roadmap change requires the money-transmitter analysis to be redone. | (a) Addressed | `BuildSpec.md` §Data Model: no transfer, redemption, or cash-out pathway exists anywhere in the Mbuck ledger schema or API surface; enforced structurally, not by policy alone. Any future roadmap change to this is flagged in `BuildSpec.md` as requiring the money-transmitter legal analysis to be redone before implementation — carried through unchanged, not silently softened. |
| 4 | POPIA Section 14 retention period and deletion trigger: not yet affirmatively designed — a named, pending build task. | (a) Addressed | `BuildSpec.md` §Compliance: concrete retention period and deletion trigger now specified (see BuildSpec) — this was a genuine open technical/data-design decision within the Developing Committee's remit and is resolved here, not carried forward. |
| 5 | Two hardening recommendations (consent-flow documentation separation; lightweight parent identity-verification) remain unbuilt. | (a) Addressed | `BuildSpec.md` §Compliance and §Screens/Flows: consent-flow is specified as a structurally separate screen/record from general onboarding, versioned and timestamped; parent identity verification is specified as SMS-OTP to the registration phone number. Both were open technical decisions within the Developing Committee's remit; both resolved here. |
| 6 | Terminology-risk mitigation (debt-coded language reserved to parent-facing surfaces) rests on reasoned judgment, not settled ARB authority. | (a) Addressed | `BuildSpec.md` §Compliance: string-resource/content-layer separation between parent-facing and child-facing surfaces specified as a concrete build constraint (separate resource namespaces, reviewed at build time). The underlying interpretive legal uncertainty itself is not eliminable by a spec (no ARB ruling exists) and is carried forward unchanged as stated risk in `BuildSpec.md`, not overstated as resolved. |

## Child Welfare / Data Privacy

| # | Verdict_v7.md item | Disposition | Mapping / Reasoning |
|---|---|---|---|
| 7 | Data-Privacy Practitioner review of the candidate breach-response commitment: not yet performed, zero-cost, trigger-defined but outstanding across multiple cycles. | (b) Accepted risk, not addressed | User-authorized deviation (one of the four carve-outs). Pre-pilot gate, not pre-build — confirmed correctly framed by both Incubator and Investment Committee. Captured as a hard, verified-completion milestone in `ExecutionInstructions.md`, explicitly requiring evidence the review occurred, not merely that its trigger is defined (see Gate Integrity Check, row 23 below). |
| 8 | Child-development specialist review of the exam-bonus motivation-probe: not yet performed, same trigger, same outstanding status. | (b) Accepted risk, not addressed | Same as row 7 — user-authorized deviation, pre-pilot hard gate, tracked in `ExecutionInstructions.md` with an evidence-of-completion requirement. |
| 9 | No quantified stop/redesign threshold exists for either the relationship-strain or motivation-probe instruments. | (b) Accepted risk, not addressed | User-authorized deviation (one of the four carve-outs). Confirmed via the hidden-technical-decision check above: this requires child-development clinical expertise, not a generic product/engineering judgment call — correctly a business/domain obligation, not something the Developing Committee should resolve by picking a number. Captured in `ExecutionInstructions.md` as a required pre-pilot deliverable, bundled with the specialist review itself (rows 7-8), since the threshold is most credibly set by the same specialist during that review. |
| 10 | Late-penalty mechanic's Family Stress Model affective pathway is "narrowed but not eliminated" — residual real-world household-conflict risk to minors as young as 6. | (a) Addressed | `BuildSpec.md` §Operations/Late-Penalty Mechanic: documents the existing mitigation design (7-Mbuck cap in production, 3-Mbuck cap in pilot; grace period/pre-escalation reminders) carried through unchanged. The residual risk is explicitly accepted, not eliminated, and is tracked via the family-relationship-strain measurement package instrumented into the pilot (see `PRD.md` §Success Metrics) as an ongoing monitoring mechanism, not a closed item. |

## Financial

| # | Verdict_v7.md item | Disposition | Mapping / Reasoning |
|---|---|---|---|
| 11 | No P&L or break-even analysis exists anywhere in this Business Case. | (b) Accepted risk, not addressed | User-authorized deviation (one of the four carve-outs). Founder-executable arithmetic task explicitly out of scope this cycle. Captured in `ExecutionInstructions.md` as a required pre-runway-commitment deliverable (see Milestones), distinct from the pilot-gated items above since this gates a financial decision point (month-6 self-fund-further trigger), not pilot enrollment. |
| 12 | Revenue funnel (92-915 paying families) rests on Guessing/Assumed-tier assumptions (2.0 children/family; 0.3-1% install capture; 1-3% conversion). | (b) Accepted risk, not addressed | Not one of the four user-authorized carve-outs — a Developing Committee judgment that this cannot be resolved via specification work: these are market-validation questions answerable only with real-world pilot/acquisition data, not engineering or founder arithmetic. Partially monitored (not validated) via the pilot's 60% task-cycle-completion checkpoint (`PRD.md` §Success Metrics), which the Business Case itself concedes tests engagement, not acquisition-volume feasibility. Flagged, not silently dropped. |
| 13 | R10,000 development budget is 45×-220× below a previously cited agency engineering-cost comparable — viable only if founder-labor-plus-AI substitution genuinely holds. | (b) Accepted risk, not addressed | Developing Committee judgment: this is a founder resourcing decision already made by the user (the budget ceiling), not an implementation choice the Developing Committee can resolve. Partial mitigation reflected in `BuildSpec.md` by keeping the architecture and dependency list deliberately lean (see §Trimmed Scope) to fit the stated budget, but the underlying sufficiency question is not eliminable by spec design. |
| 14 | Self-fund-further ceiling (R20,000 total) and its named non-dilutive funding fallback are both untested for sufficiency/obtainability. | (b) Accepted risk, not addressed | Developing Committee judgment: obtainability depends on the founder's future external actions (contacting Injini once a cohort opens; clarifying TIA eligibility directly), which are outside spec/build scope. Flagged as a required pre-month-6 milestone check in `ExecutionInstructions.md`. |
| 15 | Founder's age and MiniMoney's company-registration/SARS tax-clearance status — both unconfirmed, both gate the top two named funding-fallback candidates (NYDA, SEDA). | (a) Addressed — resolved upstream | Resolved in `BusinessCase_v24.md` (Verified-tier, via `Clarifications_v24.md`): founder age 39 excludes NYDA; current lack of CIPC registration/SARS tax clearance excludes SEDA. Carried through into `BuildSpec.md` §Compliance/Constraints as the current, narrower funding-candidate picture (Injini, TIA only). No further Developing Committee action required on the fact itself; the unresolved *consequence* of this finding is captured separately at row 14. |
| 16 | No precise sizing exists for the post-runway external funding ask; researched figures are program ceilings, not typical disbursements. | (b) Accepted risk, not addressed | Developing Committee judgment: precise sizing depends on both the (out-of-scope) P&L/break-even model (row 11) and direct engagement with the two remaining funding candidates (row 14) — neither resolvable via specification work. Flagged in `ExecutionInstructions.md` as dependent on rows 11 and 14. |

## Commercial / Go-to-Market

| # | Verdict_v7.md item | Disposition | Mapping / Reasoning |
|---|---|---|---|
| 17 | The organic-only acquisition thesis has no validation mechanism — the pilot's 60% checkpoint tests engagement, not acquisition-volume feasibility, a distinction the Business Case itself concedes. | (b) Accepted risk, not addressed | Developing Committee judgment: validating absolute acquisition-channel volume requires real-world channel testing that cannot be produced via specification work. Partial monitoring via the pilot checkpoint is captured in `PRD.md` §Success Metrics, explicitly caveated (per the Business Case's own concession) as not a volume-validation mechanism. |
| 18 | The schools-partnership channel — the strongest demonstrated local reach precedent — is deferred entirely for founder-bandwidth reasons. | (a) Addressed | `PRD.md` §Non-Goals: explicitly named as out of MVP/launch scope, carried through unchanged from the Business Case's own founder-bandwidth-based deferral decision. |
| 19 | n=10 first-party interview evidence is genuine but explicitly non-representative; must not be treated as a demand signal until superseded by the pilot or a structured survey. | (a) Addressed | `PRD.md` §Non-Goals and §Success Metrics: explicit instruction carried through that neither the n=10 interviews nor the pilot's own directional findings may be treated as a statistically validated demand signal. |
| 20 | Success-criteria benchmarks (operational health 65%, general retention) remain unbenchmarked placeholders. | (a) Addressed | `PRD.md` §Success Metrics: operational-health target (65%) retained as the founder's existing committed figure; a general 90-day retention target (distinct from the 60% v2-curriculum-trigger figure) is newly set by the Developing Committee at 40%, since this was a genuine open product decision within scope (not one of the four carve-outs) and the "no open technical decisions" mandate requires it be resolved here. Explicitly flagged in `PRD.md` as a Developing-Committee-set baseline pending real calibration against pilot/post-launch data, not a specialist- or user-validated figure. |

## Execution Capacity

| # | Verdict_v7.md item | Disposition | Mapping / Reasoning |
|---|---|---|---|
| 21 | A single founder is responsible, within one 6-month runway, for the build, an instrumented pilot, two regulatory rechecks, two specialist reviews, and manual dispute adjudication beyond 48 hours. No section assesses this as an aggregate single-point-of-failure risk. | (b) Accepted risk, not addressed | User-authorized deviation (one of the four carve-outs). Captured in `ExecutionInstructions.md` as a required deliverable before pilot enrollment and before the month-6 funding decision point, run explicitly alongside (not merged into) the two specialist reviews and the P&L. |
| 22 | The dispute-escalation interim mechanism has no stated volume or capacity threshold at which it is deemed to have failed. | (a) Addressed | `BuildSpec.md` §Operations/Dispute Handling: this was a genuine open technical/operational decision within the Developing Committee's remit (not one of the four carve-outs) and is resolved here — a concrete capacity threshold is now defined (see BuildSpec), at which the interim mechanism is deemed to have failed and escalates. |

## Process / Framework

| # | Verdict_v7.md item | Disposition | Mapping / Reasoning |
|---|---|---|---|
| 23 | A recurring pattern across at least six referenced Investment Committee cycles converts "unresolved" into "resolved via defined trigger, owner, and fallback" without completing the underlying work (Gate Integrity Check concern). The Developing Committee should trace whether the two outstanding specialist reviews are actually completed, not merely re-triggered again, before any pilot-stage work proceeds. | (a) Addressed | `ExecutionInstructions.md` §Milestone Verification: the two specialist-review milestones (rows 7-8) explicitly require documented evidence that the review occurred (e.g., a dated written opinion/sign-off from the named specialist), not merely a restated trigger definition, before pilot enrollment of any real family may proceed. This is the direct, structural response to the Gate Integrity Check concern, carried into execution rather than left as a document-level statement. |

---

## Summary

23 of 23 risk/assumption items from `Verdict_v7.md`'s Risks and
Assumptions section are disposed: 15 as (a) addressed in a named spec
section, 8 as (b) explicit accepted risk with stated reasoning. No row is
left blank. All four user-authorized carve-outs are disposed under (b)
with their reasoning distinguished from the other, non-authorized (b)
rows. No unresolved row remains before proceeding to `PRD.md`.
