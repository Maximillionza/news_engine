# Executive Summary: MiniMoney — v1

> Copied verbatim from `BusinessCase_v1.md`. This is the fixed-format
> summary for first-pass Investment Committee review.

---

## Executive Summary

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

MiniMoney is a proposed financial-education app for children and teens
(ages 6–18) that combines gamified task assignment with a simulated
payroll system: children complete parent-assigned tasks to earn points
pegged to real currency, incur percentage-based "expenses" that scale
with earnings, and receive a "payslip" summarizing earnings, overtime,
and deductions. The parent receives a corresponding invoice and is
required to transfer the actual owed funds to the child via their
registered bank account. Financial literacy education is layered on top,
tailored to the age of the user. The concept is well-formed as a family
finance/allowance-management tool with an embedded curriculum, but it
sits at the intersection of three regulated domains — payments,
child-directed digital services, and financial education — none of which
are addressed in the original submission beyond the core mechanic. This
Business Case surfaces those gaps explicitly rather than assuming they
are solved.

---

## Problem

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

Parents lack a structured, automated system to teach children (6–18)
real-world financial concepts — earning, budgeting, taxation/expenses,
and payment mechanics — using real money in a controlled, task-based
framework. Existing allowance-tracking apps (implied competitive gap, not
stated in source) typically either (a) simulate money entirely in-app
with no real bank transfer, limiting real-world stakes, or (b) require
manual parent bookkeeping with no education layer. The case study does
not cite data, research, or a personal anecdote establishing this problem
empirically — the problem statement is inferred from the described
solution mechanic, not independently evidenced in the source.

---

## Value Proposition

**Status:** Partial | **Confidence:** Medium | **Evidence:** Supported

For parents: an automated system that turns household chores/tasks into
a structured payroll-like experience for their children, removing manual
tracking and adding a built-in financial literacy curriculum, with
expense rules that scale proportionally to earnings (so the system
remains meaningful regardless of how much or little a child earns). For
children: a "real job" simulation — payslips, overtime, deductions — that
pays out in actual money via their parent's bank transfer, tied to
age-appropriate lessons. This is the strongest, most concrete part of the
original submission. What is not addressed: why a parent would choose
this over simply paying an allowance manually, or over a competing app;
no differentiation claim is made in the source itself.

---

## Business Model

**Status:** Incomplete | **Confidence:** Low | **Evidence:** Unknown

Not addressed in the case study. No monetization mechanism (subscription,
freemium, transaction fee, bank partnership revenue share, B2B2C via
banks/schools) is specified. The core mechanic implies MiniMoney is a
facilitation/education layer sitting on top of the parent's own bank
account — it is not itself described as moving or holding money (the
parent pays the child "via their registered bank," suggesting the app
may not need a money-transmitter license if it never touches funds
directly — but this is an inference, not a stated design decision, and
must be validated with a payments/compliance expert).

---

## Readiness Score

**Readiness Score = 23 / 135 = 17%**

**This score is below the 70% completion gate threshold.** Legal &
Compliance and Child Data & Consent are both Critical + Incomplete,
which independently fails the gate regardless of overall score.

### Critical Gaps
1. **Legal & Compliance (Critical, Incomplete)** — no jurisdiction,
   licensing, or money-transmission analysis exists; this is the single
   largest blocker to feasibility.
2. **Child Data & Consent (Critical, Incomplete)** — no parental consent
   framework, data minimization approach, or app-store child-category
   compliance plan exists for users as young as 6.
3. **Business Model / Revenue & Costs / Market & Competition** — entirely
   unaddressed; the Investment Committee cannot assess viability without
   at least a directional monetization and competitive stance.
4. **Objectives / Success Criteria / Validation Strategy** — no
   measurable definition of what success looks like or how it would be
   tested exists yet.
