# Clarifications v11 — MiniMoney

## 1. "Request for payment" feature — removed

Resolves the v10 Critical Gap / Outstanding Question raised when the late-penalty
redesign (parent alone incurs the penalty, zero child visibility) was corrected
across BusinessCase_v10.md.

The child-facing "request for payment" feature (present since Clarifications_v5.md)
presupposed the child could see arrears — including the penalty-inclusive figure —
in order to know when to invoke it. Under the corrected zero-child-visibility
penalty design, that precondition no longer holds.

User confirmed (2026-07-08, off-cycle) that "arrears" in this feature previously
meant the penalty-inclusive figure — i.e. reading #2 of the two possibilities
v10 flagged. This makes the feature incoherent as originally described.

**Decision: remove the feature entirely, for now.** Not a redesign to reference
only the child's unpaid base wages — full removal. "For now" per the user's own
framing — leave open the possibility of a future reintroduction (e.g. scoped to
base-wage-only arrears) as a later design decision, not a default assumption in
this revision.

Incubator instruction: remove all references to the "request for payment"
feature across every section that currently describes it (Operations and any
other section touching the payment/late-penalty/arrears flow), rather than
leaving a stale description in place. Do not invent a replacement mechanic.

## 2. ResearchFindings_v2.md — to be incorporated this cycle

Already delivered by Research House (Engagement 2, enforcement-mechanism
research — read-only account-linking/open-banking options, enforcement
landscape, comparable-app practices, cost/complexity scoping). Per standing
routing rules, treat as vendor output requiring the Incubator's own scrutiny,
never as trusted or Verified-tier evidence on its own.
