# Clarifications for MiniMoney — supplied after Investment Committee "proceed with changes" verdict, resolving v9's remaining open items

> These are additional facts and design decisions supplied by the user in
> response to BusinessCase_v9.md's five remaining open items (all
> originating from the Investment Committee's six required changes). Not
> a pivot — the original premise is unchanged. Treat these as
> authoritative additions, to be incorporated into BusinessCase_v10.md.

## Date
2026-07-08

## Raw clarification — subscription price point (verbatim from user)
"for the subscription it will start at R59.99 a month which will allow
upto 4 kids per family."

## Raw clarification — legal-opinion trigger (verbatim from user)
"The legal opinion will be gathered as soon as we have a stable working
model and before any pilot testing with real people commences."

## Raw clarification — 90-day onboarding target (verbatim from user,
## across two messages)
First message: "We are targeting onboarding atleat 100 a day for the
first 90 days." Second message, resolving the Chief of Staff's follow-up
question about whether this replaces or supplements the existing
15,000-in-90-days figure: **"The 100 per day is the floor target with
the intention to increase the adoption rate above this."**

## Raw clarification — late-penalty mechanic redesign (verbatim from
## user, across two messages, second message is the final design)
First message: "The child wont incur the penalty, it will be visable to
the child if a penalty was charged and how much is owed to them due to
late fees." Second message, simplifying further and superseding the
first: **"For a cleaner implementation, lets remove the visability to
the child for the penalties incurred by the parent and the parent
incurs the penalty not the child."**

**Final design (this supersedes every prior version's description of
this mechanic):** the escalating late-penalty (5→6→7 Mbucks/week,
pilot cap 3) is incurred entirely by the parent, not the child. The
child has **no visibility whatsoever** into whether a penalty was
charged or how much is owed — this is purely a parent-side
administrative/financial matter, invisible to the minor's account, UI,
statements, or reports.

## Raw clarification — n=10 interview data (verbatim from user)
"accept it stays bounded as non-representative."

## Relevant to which BusinessCase_v9.md gaps

- **Value Proposition / Business Model / Financial Considerations
  (Investment Committee requirement #2):** resolved. Subscription price
  is R59.99/month, covering up to 4 children per family account. This
  should now be used to model absolute revenue against the existing
  Year-1 funnel range (360-2,440 paying subscribers), where previously no
  price point existed to do so.

- **Legal & Compliance (Investment Committee requirement #1, the "firm
  trigger" sub-item flagged as still open in v9):** resolved with an
  event-based (not calendar-dated) trigger: the specialist legal opinion
  will be commissioned once a stable working model exists, and before any
  pilot testing with real families begins. This is consistent with the
  user's established preference for directional rather than granular
  timelines (per Constraints, v8).

- **Objectives / Risks (Investment Committee requirement #3, the
  90-day-vs-annual-funnel tension):** resolved. 100/day is confirmed as a
  **floor**, not the target itself — the intention is to grow adoption
  above this floor over the 90-day window, which is the front-loaded/
  ramping rationale the Investment Committee asked be stated explicitly
  (rather than left as an unreconciled number). The Incubator should
  restate the 15,000-in-90-days figure as the aspirational total
  consistent with growth above a 100/day floor, not a flat-rate
  calculation.

- **Operations / Success Criteria / Risks / Legal & Compliance —
  Child Data & Consent (Investment Committee requirement #5, the
  child-development/age-appropriateness review):** the late-penalty
  mechanic's design has changed substantively, not merely been
  re-described. Every version from v5 through v9 characterized this as a
  penalty visible to and (in earlier readings) financially affecting the
  minor — the Risks section in multiple versions states "a minor is
  financially penalized for the parent's own delay." **This
  characterization must now be corrected, not merely supplemented,**
  across every section that currently describes it that way (Operations,
  Success Criteria, Risks, Legal & Compliance, Legal & Compliance — Child
  Data & Consent extension, Assumptions, Critical Gaps, Outstanding
  Questions). The corrected design: the parent alone incurs and is
  responsible for the penalty; the child has no visibility into it at
  all. The Incubator should assess whether this substantially narrows
  (though perhaps does not fully eliminate — a parent's own stress or
  behavior around an accumulating obligation could still indirectly
  affect the child) the child-development risk the Investment Committee
  flagged, since the child no longer sees or bears the penalty directly.
  **Please also check for a consistency question this redesign
  introduces:** prior versions (from `Clarifications_v5.md` onward)
  described a feature where "minors can generate 'request for payment'
  prompts after month 1 and every month the arrears are not settled" —
  if the child has zero visibility into arrears/penalties, the Incubator
  should flag whether this feature is still coherent as designed, or
  whether it also needs to be reconciled/removed/redesigned.

- **Enforcement of the penalty (new, not yet addressed in any version):**
  the user has separately flagged that *enforcing* this parent-side
  penalty — i.e., confirming or compelling that the parent actually pays
  it, given MiniMoney has no banking-rail visibility — requires
  additional research, and has asked that Research House be engaged on
  this specific question. This is being issued as a separate Research
  House task order (Engagement 2), not addressed within this Incubator
  cycle. The Incubator should note in v10 that this specific sub-question
  is pending a vendor engagement, distinct from the design clarification
  itself (which is resolved).

- **Supporting Evidence (Investment Committee requirement #6):**
  resolved — the user accepts the Incubator's proposed bounding of the
  n=10 interview data (non-representative, not to be used as validated
  demand evidence) rather than commissioning methodology documentation.
