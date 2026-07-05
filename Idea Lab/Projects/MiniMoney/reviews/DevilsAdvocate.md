# Devil's Advocate Review: MiniMoney — v1

> Objections below each cite a specific Business Case section by name
> and argue the strongest case against proceeding as currently scoped.

---

### Objection 1 — Legal & Compliance is not merely incomplete, it may be disqualifying

The **Legal & Compliance** section of `BusinessCase_v1.md` currently
carries no jurisdiction, no licensing analysis, and no confirmation of
whether MiniMoney's invoice-triggered bank payment constitutes regulated
money transmission. This is not a gap that can be filled later with
"more detail" — if the answer turns out to be "yes, this requires an
e-money or payment-facilitator license," the entire cost structure,
timeline, and even viability of the product changes. The Business Case
should not proceed to Investment Committee review with this section
still Incomplete; a preliminary legal opinion (even informal) should be
a prerequisite, not a downstream task.

### Objection 2 — The Business Model section provides no reason to believe this is a viable business, only a viable feature

The **Business Model** section is entirely Incomplete: no monetization
mechanism is specified anywhere in the source. It is entirely possible
that MiniMoney is a compelling feature bolted onto an existing family
banking app (e.g. a bank-partnership feature) rather than a standalone
venture with its own defensible revenue model. Without at minimum a
directional answer — subscription vs. freemium vs. B2B2C — the
**Market & Competition** section cannot be meaningfully populated either,
since pricing and competitive position are inseparable. As written, this
Business Case describes a product mechanic, not a business.

### Objection 3 — The Value Proposition section asserts differentiation the case study does not actually support

The **Value Proposition** section claims the payroll-simulation mechanic
(payslip, overtime, invoice) is "the strongest, most concrete part of
the original submission," but this framing risks over-crediting the
idea's novelty. The case study never claims to have researched whether
this mechanic already exists in competing products, and the
**Market & Competition** section confirms zero competitive analysis was
performed. The Investment Committee should treat the Value Proposition
section's confidence rating (Medium) with skepticism until a
competitive scan actually confirms the payslip/invoice framing is
differentiated rather than assumed differentiated.

### Objection 4 — The Risks section identifies a "terminology risk" but the Business Case does not go far enough on child-psychology implications

The **Risks** section flags that framing a child's allowance as
"payslip," "overtime," and "expenses" could raise concerns about
normalizing labor-like relationships between parent and child, but this
is listed as a single bullet among five and not escalated to a Critical
gap or given its own domain-extension section, unlike Legal & Compliance
and Child Data & Consent. Given that this product is explicitly aimed at
children as young as 6, the psychological/developmental framing of
"earning a payslip for chores" deserves the same weight as the
regulatory gaps — the current Business Case under-weights this by
treating it as a minor risk bullet rather than a section requiring its
own expert sign-off (partially addressed via the Curriculum Design
extension, but that section focuses on educational content, not on the
psychological appropriateness of the payroll metaphor itself).

### Objection 5 — Outstanding Questions section is marked "Complete," which may understate how foundational these gaps are

The **Outstanding Questions** section is tagged Status: Complete because
it successfully lists ten open questions — but "Complete" as a status
here is somewhat misleading to a reader skimming statuses, since the
existence of ten unresolved foundational questions (jurisdiction,
whether funds are ever held by the app, monetization model, enforcement
mechanism) is itself evidence the underlying case is far from ready.
The Investment Committee should not read "Outstanding Questions:
Complete" as a positive signal — it means the list-making task is
complete, not that the questions have answers.
