# Engagement Brief — Specialist Legal Opinion

> Prepared for external use: to be sent to a South African legal
> specialist. Not a Panel or Vendor work product — compiled by the Chief
> of Staff directly from BusinessCase_v15.md and Verdict_v2.md for the
> user's own outreach. Contains no fabricated legal analysis; every
> question below is a real open item this case has been unable to
> resolve through desk research alone.

## What MiniMoney is
A financial-education mobile app (Android-first) for children and teens
aged 6-18, launching in South Africa. Children complete parent-assigned
tasks to earn a real-money-pegged in-app currency ("Mbucks," e.g. 10
Mbucks = R10) alongside a separate non-monetary cosmetic-reward currency
("Mpoints"). The app generates a parent-facing "invoice" and a
child-facing "payslip"; the parent then pays the child the owed amount
directly via the parent's own banking app — **the app itself never
holds, moves, or takes custody of any funds.** A minor cannot access any
part of the app, including educational content, without a
pre-existing, consenting parent account (universal parental-consent
gate, no exceptions). Monetization is a parent-only subscription
(R59.99/month, up to 4 children); no in-app purchase is ever available
to a minor. An escalating late-payment penalty (5→6→7 Mbucks/week) is
incurred entirely by the parent if a scheduled payment isn't marked
complete on time — the child has no visibility into whether this penalty
was charged. Read-only bank-account-linking (e.g. Stitch/Mono-style, to
help verify payment occurred) is planned as an optional, parent-opt-in
feature, not mandatory and not yet built.

## Why now
This case has gone through fifteen internal revisions and two rounds of
desk research (via a research vendor) narrowing these questions as far
as non-legal research can take them. An independent review body
concluded the case cannot proceed further without an actual legal
opinion — the remaining questions require your judgment, not more
internal iteration.

## Specific questions requiring your opinion

1. **Money-transmitter / payment-facilitation characterization.** Does
   the invoice → payment-trigger → payslip mechanic, despite the app
   never holding or moving funds itself, risk being characterized as
   regulated payment facilitation under South African law?

2. **POPIA Section 34/35 sufficiency of the consent model.** The app now
   uses a single, universal rule: no minor may access any part of the
   app without a pre-existing, consenting parent account (no carve-outs
   of any kind — an earlier design allowing limited pre-consent minor
   registration was removed specifically because of this open question).
   Is this consent model, as described, sufficient under POPIA's
   competent-person consent requirements?

3. **POPIA Section 14 retention sufficiency.** Our own research found
   POPIA's general data-retention principle (information not retained
   longer than necessary; correction/deletion on request within 30 days)
   but found no minor-specific supplementary retention rule (comparable
   to COPPA or GDPR-K) within POPIA itself. Is the general principle
   sufficient for this specific data model, or is additional design
   needed?

4. **Minor contractual capacity.** The payment obligation is structured
   to run against the parent, not the child — the child is a
   participant who is remunerated on task completion, not a party bound
   by any enforceable obligation. Our own (non-legal) research found no
   South African law or act that appears to bar this specific
   parent-child arrangement, but this has not been confirmed by counsel.
   Does this structure hold up, and does the "domestic agreement"
   presumption (that family arrangements are not intended to be legally
   binding) affect how the payslip/invoice mechanic should be
   characterized or documented?

5. **Terminology risk.** Our research confirmed **no existing ARB ruling
   or National Credit Regulator guidance addresses this exact question**
   — this is a genuine gap in precedent, not something we simply
   couldn't find. Does applying employment/consumer-debt terminology
   ("payslip," "invoice," "late penalty," "arrears") to a product
   directed at children as young as 6 carry any regulatory or
   advertising-standards risk under the ARB's Code of Advertising
   Practice (Clause 14, which prohibits exploiting children's credulity
   or inexperience) or elsewhere?

6. **NCR scope on optional account-linking.** Our own research found
   that NCR registration is anchored to four defined categories (credit
   providers, credit bureaus, debt counsellors, Payment Distribution
   Agents), none of which appears to plausibly cover a read-only,
   non-custodial bank-account-verification integration (e.g.
   Stitch/Mono-style). Can you confirm whether offering this as an
   *optional* parent-controlled feature (never mandatory) would trigger
   NCR or any other South African payment-services regulatory
   obligation?

7. **App-store child-category cross-check.** We've identified that
   Google Play's Families Policy and Apple's Kids Category guidelines
   both impose disclosure/design requirements on the app's non-monetary
   rewards system (Mpoints) independent of any real-money transaction.
   Is there any South African-specific regulatory overlay on top of
   these platform policies we should be aware of?

## Already scoped, to save your time
- **Cost range** (our own prior desk research, non-binding): roughly
  R25,000-R80,000 for a bespoke opinion covering the above.
- **Firm shortlist identified in prior research** (not vetted or
  contacted by us): Caveat Legal, VeraSafe, PPM Attorneys, Bregman
  Moodley Attorneys, MJ Kotze Inc.
- **Suggestion, not a decision:** given cost, consider requesting a
  short, cheaper preliminary read on items 1 and 5 (the two highest-
  stakes questions) before committing to the full bespoke opinion.

## What happens with your answer
This case is paused pending your input. Whatever you determine will be
incorporated into the next Business Case revision and re-reviewed before
any further build work proceeds on the features currently gated behind
this opinion (invoice generation, payment-confirmation workflow,
late-penalty calculation, the data-retention pipeline, and the optional
account-linking feature).
