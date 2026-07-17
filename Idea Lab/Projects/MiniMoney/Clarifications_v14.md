# Clarifications for MiniMoney — v14

> Two design decisions resolving open items in BusinessCase_v13.md's
> Legal & Compliance / Critical Gaps, made in direct response to
> ResearchFindings_v3.md. Not a pivot. To be incorporated into
> BusinessCase_v14.md.

## Date
2026-07-09

## 1. Pre-link independent-registration carve-out — removed (verbatim
## from user)
"Pre-link registration carve-out - remove the functionality and force a
minor to have a parent be the registration custodian."

**Final design:** the pre-link independent-registration carve-out
introduced in `Clarifications_v12.md` (a minor could install, register,
and access a practice-only "budgeting" feature before any parent link
existed) is removed entirely. A minor cannot register an account at all
without a parent acting as the registration custodian — this reverts to
and reaffirms the universal parental-consent gate established in
`Clarifications_v5.md` ("collapse everything behind parental consent"),
closing the narrow exception that had reopened the question in v12/v13.

**Relevant to:** this directly resolves BusinessCase_v13.md's Critical
Gap #3 (pre-link independent-registration carve-out) and the
corresponding item in Legal & Compliance and Legal & Compliance — Child
Data & Consent. The Incubator should remove all references to
independent minor registration and the pre-link practice-budgeting
feature across every section describing it (Operations, Technology,
Value Proposition, Stakeholders, Target Users/Customers, Legal &
Compliance, Risks, Assumptions, Roadmap, Validation Strategy, Outstanding
Questions, Critical Gaps), consistent with the case's established
practice (per Playbook Entry 2) of treating a reverted design as a
correction, not a stale-but-supplemented description — and checking
whether anything else in the case implicitly depended on the now-removed
carve-out (e.g. the Executive Summary's platform/feature description,
or Financial Considerations' family-vs-child install-count assumptions).

## 2. Read-only account-linking (Stitch/Mono) — made optional, not
## excluded (verbatim from user)
"excluding Stitch/Mono : - Add this a optional feature the parent can
use and not a mandatory feature as some parents may not feel comfortable
with linking their bank information regardless if its read only"

**Final design:** rather than excluding read-only account-linking
entirely (the `Clarifications_v10.md` decision, whose NCR-avoidance
rationale `ResearchFindings_v3.md` found likely mistaken), MiniMoney
will offer account-linking (Stitch/Mono-style) as an **optional,
parent-controlled feature** — a parent may choose to link a read-only
view of their bank account to help verify payment, but is never required
to. The user's stated reason for optionality is not solely the
now-questioned NCR concern, but also parent comfort: some parents may
not want to link banking information to a third-party app even on a
read-only basis, regardless of the regulatory position.

**Relevant to:** this resolves BusinessCase_v13.md Critical Gap #4's
sharpened sub-question (whether MiniMoney is needlessly forgoing a
risk-reducing feature) by no longer forgoing it, while preserving the
existing honor-system self-report path as the default for parents who
decline to link. The Incubator should update Operations, Technology,
Business Model, Risks, Roadmap, and Validation Strategy to describe this
as a genuine product feature (parent-opt-in account-linking, alongside
honor-system self-report as the default/fallback), not merely note the
NCR premise was questioned. The underlying regulatory question (does the
NCR, or any other SA regulator, actually reach this kind of service) is
still not definitively answered by desk research and remains an item for
the specialist legal opinion before this optional feature should ship,
consistent with the existing feature-level build-gating plan (v9).
