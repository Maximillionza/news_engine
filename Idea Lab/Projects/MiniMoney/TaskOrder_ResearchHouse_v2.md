# Task Order: Research House — Engagement 2 — MiniMoney

> Issued by the Chief of Staff. This is a follow-on engagement for the
> same case study as Engagement 1. Read your own EngagementLog.md first
> to continue from your prior work on this case — do not import context
> from any other case study. This task order is self-contained; you have
> not been given the Business Case document itself.

## Case
MiniMoney — financial-education app for children aged 6-18, South
Africa, Android-first, Freemium (subscription-based) model. Parents pay
children directly via the parent's own banking app — MiniMoney never
holds, moves, or has visibility into whether the payment occurred.

## Background for this engagement
The product includes an escalating late-payment penalty charged to the
**parent** (never the child) if the parent fails to mark a scheduled
payment as complete on time. The penalty currently has no enforcement
mechanism: MiniMoney cannot detect or verify whether the parent has
actually paid anything (the core payslip amount, or the late penalty)
because it has no integration with any banking rail. The current design
relies entirely on the parent self-marking payment as complete, with the
minor able to dispute that claim.

## What is being asked
Research practical mechanisms — technical, contractual, or behavioral —
for verifying or encouraging real compliance with this payment/penalty
obligation, without MiniMoney itself becoming a money transmitter or
payment processor (that would reintroduce the money-transmission
licensing risk this case has already substantially avoided by design —
do not propose anything that would require MiniMoney to hold or move
funds itself).

Specifically:

1. **Read-only account-linking / open-banking-style verification
   services available in South Africa** (e.g. Stitch, Mono, or bank-
   specific APIs/aggregators) that could let a parent optionally link a
   read-only view of their bank account, so the app could detect that an
   outgoing/incoming transaction matching the expected amount occurred —
   without the app ever holding or routing the money itself. Identify
   what exists, roughly how it's priced/licensed for a small startup, and
   what data-privacy obligations (beyond what POPIA already requires for
   general personal data) such a service would likely introduce.

2. **Whether a parent's in-app arrears/penalty balance would have any
   real contractual or legal enforceability** in South African family/
   consumer context (e.g. is this simply a private, unenforceable family
   arrangement the app merely tracks, similar to a personal IOU, or does
   structuring it as a formal "agreed condition of the budget setup" (as
   this app does) change that) — flag clearly that a binding legal
   answer requires the specialist legal opinion already planned for this
   case, and that your role here is to surface the practical landscape,
   not give a legal conclusion.

3. **How comparable family-finance or kids'-allowance apps (local or
   international) handle this same problem** — i.e., verifying an
   external, unintegrated bank payment occurred, without becoming a
   payment processor themselves. Is honor-system self-reporting (what
   MiniMoney currently does) standard practice in this category, or do
   any comparable products solve it differently?

4. **Rough cost/complexity scoping only** (not a firm quote) for the
   read-only account-linking option in item 1, if you find one that looks
   viable for a solopreneur, AI-assisted development approach — is this
   realistically in scope for an early build, or squarely a later-stage
   feature?

## What is explicitly NOT being asked
- Do not attempt to give a binding legal opinion on enforceability — flag
  that as requiring the specialist legal opinion, and describe only what
  you can find about the practical/precedent landscape.
- Do not propose any mechanism that would require MiniMoney itself to
  hold, transmit, or take custody of funds — that reintroduces a
  regulatory risk this case has deliberately avoided.
- Do not fabricate a South African-specific pricing figure for
  account-linking APIs if none is publicly available — say so and
  estimate only what a direct vendor inquiry would likely take.

## Engagement log
Path: `Projects/MiniMoney/EngagementLog.md` — this already exists from
Engagement 1. Read it first, then update it to include this engagement.

## Output
Write your findings to `Projects/MiniMoney/ResearchFindings_v2.md`. Do
not read `BusinessCase_v9.md`, `BusinessCase_v10.md`, or any other
Business Case file — this task order is self-contained.
