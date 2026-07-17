# Task Order: Research House — Engagement 3 — MiniMoney

> Issued by the Chief of Staff, following a formal Confidence/Evidence
> trigger (both Critical sections dropped to Confidence: Low in
> BusinessCase_v12.md). Read your own EngagementLog.md first to continue
> from your prior work on this case — do not import context from any
> other case study. This task order is self-contained; you have not been
> given the Business Case document itself.

## Case
MiniMoney — financial-education app for children aged 6-18, South
Africa, Android-first, subscription-based. Parents pay children directly
via the parent's own banking app — MiniMoney never holds or moves funds.
A specialist POPIA/ARB/contract-law legal opinion is planned but not yet
commissioned.

## Background for this engagement
Two new design decisions were made this cycle that raise specific,
narrow legal/regulatory questions distinct from the broader legal
opinion still pending:

1. A minor may now independently download, register, and create an
   account before any parent account is linked. Before linking, the
   minor's account can access exactly one feature: a practice-only
   "budgeting" tool where the minor manually enters hypothetical income
   data (not real earnings). Registration itself requires capturing some
   personal information (e.g. name, age/date of birth, possibly an
   email address) to create the account.

2. The product deliberately does NOT integrate any read-only
   bank-account-linking service (e.g. Stitch, Mono) to verify payment,
   relying instead on parent/child self-reporting. The stated rationale
   is that integrating such a service would trigger National Credit
   Regulator (NCR) requirements around facilitating payments that the
   product wants to avoid.

## What is being asked

1. **Does mere account registration by a minor — independent of what
   feature they subsequently access — constitute "processing" of a
   minor's personal information under POPIA, such that competent-person
   (parental) consent would be required *before* registration itself,
   not just before accessing financial features?** Research what is
   publicly documented about POPIA's application to the *registration/
   account-creation step* specifically (as distinct from in-app feature
   use) for apps or services directed at children. Also note whether the
   practice/hypothetical nature of any data entered afterward (not real
   financial information) has any bearing on this specific question, or
   whether that is a separate, later consideration.

2. **Does the National Credit Regulator (NCR), or any other South
   African regulator, actually treat read-only bank-account-linking/
   open-banking-style verification services (of the kind Stitch or Mono
   provide) as regulated "payment facilitation" requiring NCR
   registration or similar compliance?** Research what NCR registration
   actually covers (e.g. credit providers, debt collectors, payment
   distribution agents) and whether a read-only, non-custodial
   verification integration (one that never moves money, only confirms a
   transaction occurred) would plausibly fall within that scope, or
   whether this rationale for excluding account-linking may be based on
   a misunderstanding of what NCR registration actually requires.

## What is explicitly NOT being asked
- Do not give a binding legal conclusion on either question — this
  research informs, but does not replace, the specialist legal opinion
  already planned for this case. Flag clearly where the honest answer is
  "this requires a lawyer to confirm," rather than stretching a
  precedent or guideline to sound more conclusive than it is.
- Do not fabricate a South African regulatory citation if you cannot
  find one — state plainly if no clear public guidance exists on either
  question.

## Engagement log
Path: `Projects/MiniMoney/EngagementLog.md` — this already exists from
Engagements 1 and 2. Read it first to continue with full continuity,
then update it with this third engagement.

## Output
Write your findings to `Projects/MiniMoney/ResearchFindings_v3.md`. Do
not read any BusinessCase file for this case — this task order is
self-contained.
