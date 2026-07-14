# Execution Instructions: MiniMoney

> Written directly to you, the founder. This is the handoff from the
> Developing Committee — the last stage of the Idea Lab review pipeline
> for this case. Everything below assumes you are about to start actual
> build work.

> **Correction log — 2026-07-13, pre-Milestone-1, founder-identified.**
> You caught a gap in the Mbuck currency-precision design before writing
> any code: `PRD.md` and `BuildSpec.md` are corrected accordingly (see
> the correction notes at the top of each). Because the gap concerns the
> exact shape of the `MbuckLedgerEntry`/`Budget` schema — the same schema
> this document's "first instruction to begin execution" tells you to
> build first — that instruction below is updated to fold in the
> precision fix, so you don't build the schema once and then rework it.

> **Correction log — 2026-07-14, pre-Milestone-1, Chief-of-Staff-traced.**
> A percentage-of-budget task earn-rate mechanic — sourced from this
> case's own original design record (`BusinessCase_v5.md`/
> `Clarifications_v5.md`) and restored into `PRD.md` and `BuildSpec.md` —
> also concerns the same first-commit `Task` schema this document's "first
> instruction to begin execution" tells you to build first. That
> instruction and Milestone 1's QA checklist below are updated accordingly,
> for the same reason as the 2026-07-13 correction above: build the
> `earn_mode`/`earn_value` fields and the truncate-then-floor-to-1
> calculation into the first commit, not as a follow-up rework.

## What to open, and where

Work from the `Projects/MiniMoney/` folder. You need four files open
together for the build itself:

- `PRD.md` — what to build and why; personas, features, non-goals,
  success metrics. Read this first, in full, before opening `BuildSpec.md`.
- `BuildSpec.md` — how to build it; architecture, data model, screens,
  dependencies, and every compliance requirement translated into a
  concrete technical constraint. This is your working build reference.
- `TraceabilityMatrix.md` — a record of every risk and open item the
  Investment Committee flagged, and exactly how each was either resolved
  or explicitly accepted as an open risk. Read this once before you start,
  then treat it as a background reference, not a working document.
- `BusinessCase_v24.md` — the underlying business record. You do not need
  it open while building; refer back to it only if `PRD.md` or
  `BuildSpec.md` cites a specific figure or decision you want the full
  reasoning for.

**Confirmation these are final:** `BusinessCase_v24.md` and `Verdict_v7.md`
are the final, confirmed inputs to this cycle — no further Incubator or
Investment Committee revision is pending. `PRD.md`, `BuildSpec.md`,
`TraceabilityMatrix.md`, and this file are the Developing Committee's
final output for this cycle. There is no version N+1 of any of these four
files pending review.

## The exact first instruction to begin execution

Open `BuildSpec.md` §Architecture Overview, §Data Model, and §Mbuck
Precision & Truncation Rule. Set up the project scaffold (Kotlin, MVVM,
Hilt, Room, Jetpack Compose) and implement the data model exactly as
specified there — in particular, build the `MbuckLedgerEntry` schema with
**no transfer, redemption, or cash-out endpoint**, from the very first
commit. This constraint is the technical foundation the entire
low-money-transmitter-risk legal finding depends on (`LegalOpinion_v1.md`
Q1) — get it right structurally before building anything else, not as a
later hardening pass.

**Corrected 2026-07-13 — build this into the same first commit, not as a
follow-up:** every Mbuck-typed field (`MbuckLedgerEntry.amount`, the
`Budget` entity, `LatePenaltyEvent` amounts) is a whole-number integer
type from the start — no `Decimal`/`Float` field with cosmetic rounding
layered on top later. The `Budget` input screen has no decimal/cents
input control at all, validated server-side as well as client-side. Get
the integer-only schema shape right in this first commit, the same
discipline as the non-transferability constraint above — reworking a
decimal-typed field to integer later is exactly the kind of rebuild this
instruction exists to avoid.

**Corrected 2026-07-14 — also build this into the same first commit:** the
`Task` entity includes `earn_mode` (enum, `FIXED`/`PERCENTAGE`, set per
task by the parent) and `earn_value` (whole-Mbuck integer in `FIXED`
mode; whole-number integer percentage in `PERCENTAGE` mode — no
fractional percentages). For `PERCENTAGE` mode, implement the calculation
as: (1) compute `budget × earn_value / 100`; (2) truncate toward zero to
a whole Mbuck (no rounding, no carry-forward); (3) if the truncated
result is 0, floor it to 1 — never write 0 to the ledger. Enforce the
1-Mbuck-per-task minimum at the ledger-write level in both modes, not
just UI validation. See `BuildSpec.md` §Data Model (Task) and §Mbuck
Precision & Truncation Rule for the full detail. This is the same
first-commit data model as the non-transferability constraint and the
whole-Rand/no-cents Mbuck precision rule above — get all three right
together, not as separate passes.

After the data model, build in this order: consent/registration flow →
budget/task/earning loop → payslip/payment-confirmation flow →
dispute-handling flow → late-penalty mechanic → exam-bonus mechanic
(build/QA only, not enabled for real families — see Milestones below).
Mpoints and account-linking screens can be built at any point but must
ship behind their feature flags, OFF.

## What to check at each milestone

**Milestone 0 — before writing any code.** Confirm you have read
`PRD.md` in full, in particular §Non-Goals and §Success Metrics. These
numeric targets (65% operational health, 40% general 90-day retention, 60%
pilot acquisition/engagement checkpoint, the dispute-escalation capacity
threshold) are your QA/build acceptance criteria — build toward them, not
against a vaguer sense of "done."

**Milestone 1 — foundational build complete.** Confirm all three launch
configurations (full; without account-linking; without Mpoints) build and
run correctly, per `BuildSpec.md` §Compliance. This is a QA gate, not
optional polish — the app's regulatory posture depends on both disabled
configurations actually working, not just compiling. **Added
2026-07-13:** as part of this same milestone, confirm the budget-input
screen rejects any cents/decimal entry (validation, not just display),
and confirm no Mbuck-typed field anywhere in the schema is a decimal/
float type — spot-check this in all three configurations, since the
`ACCOUNT_LINKING_ENABLED` display path is the one place a fractional
currency value (ZAR) is ever shown, and it must never leak back into the
Mbuck ledger. **Added 2026-07-14:** as part of this same milestone,
confirm `PERCENTAGE`-mode task creation produces the correctly
truncated-and-floored Mbuck value — specifically, test at least one case
where `budget × earn_value / 100` truncates to a non-zero whole Mbuck
(confirm no rounding occurred), and at least one case where it would
truncate to 0 (confirm the ledger-written value is floored to 1, never
0). Confirm `FIXED`-mode task creation still rejects a 0 entry at input.

**Milestone 2 — before any pilot enrollment of a real family (hard gate,
do not skip or soft-pedal this).** All of the following must be true, with
documented evidence, not merely restated intentions:

- The Data-Privacy Practitioner (Expert Roster Entry 5) has actually
  reviewed the data-breach/incident-response commitment, and you hold a
  dated, written sign-off or set of revisions from that review.
- The child-development specialist (Expert Roster Entry 2) has actually
  reviewed the exam-bonus motivation-probe, and you hold a dated, written
  sign-off or set of revisions from that review.
- That same child-development specialist review has produced a
  **quantified stop/redesign threshold** for both the family-relationship-
  strain measurement package and the motivation-probe — i.e., a stated
  result that would halt or force redesign of the pilot. This does not yet
  exist and is not something you or the Developing Committee should
  invent — it requires the specialist's own clinical judgment, ideally
  produced during the same engagement as the review above.

This case's Verdict (`Verdict_v7.md`) specifically flagged a recurring
pattern across at least six prior review cycles of treating "review
trigger defined" as equivalent to "review completed." Do not repeat that
pattern here. A calendar invite, an email sent, or a stated intention to
engage the reviewer does not satisfy this milestone — only a completed
review with documented output does.

**Milestone 3 — before the month-6 funding decision point (self-fund-
further trigger, or before approaching Injini/TIA).** Confirm you have:

- Produced the minimal P&L/break-even model (fixed costs — R10,000 build,
  R20,000 self-fund ceiling — against per-family contribution margin at
  R59.99/month). This is founder-executable arithmetic; it does not
  require external review.
- Checked whether an Injini cohort has opened, and/or clarified TIA's
  eligibility for a solo, non-research-affiliated consumer-app founder
  directly with TIA. Do not assume either is available without checking.

**Milestone 4 — ongoing, not a single checkpoint.** Track your own
aggregate capacity across the build, the pilot, the two regulatory
rechecks (SARB/NPS Act; FPB), the two specialist reviews, and manual
dispute adjudication. `Verdict_v7.md` and `BusinessCase_v24.md` both flag
that no section anywhere in this case's history has assessed this as a
combined, concurrent risk — each obligation has only ever been assessed
individually. You are the only person who can produce this assessment.
Revisit it explicitly at Milestones 1, 2, and 3 above, not just once.

## Files locked / not to be touched mid-build

- `BusinessCase_v24.md`, `Verdict_v7.md`, and every prior versioned file
  in this case folder (`BusinessCase_v1.md` through `v23`,
  `Clarifications_v*.md`, `FullReview*.md`, etc.) are the historical
  record of this case. Do not edit them. If something in `PRD.md` or
  `BuildSpec.md` turns out to be wrong once you're building, fix it there,
  and note the change and reason at the top of the file — do not silently
  edit `BusinessCase_v24.md` to match.
- `TraceabilityMatrix.md` is a point-in-time record of how this cycle's
  risks were disposed. Do not edit it to mark items "resolved" as you
  complete them — instead, record completion evidence in your own build
  log or in `ExecutionInstructions.md`'s Milestones section (append, don't
  overwrite).
- `PRD.md` and `BuildSpec.md` are your working build documents and may be
  revised as you build — but treat any revision as deliberate, not
  incidental: if a decision recorded there changes, say so explicitly at
  the point of the change, the same discipline the Business Case itself
  used throughout its 24 versions.

## One thing to hold in mind throughout

Two of the four items carried forward to this stage (the specialist
reviews and the child-welfare stop/redesign threshold) exist specifically
to protect real children in your pilot. They are gated at "before pilot
enrollment," not "before build," on purpose — you can and should build
now. But the gate at Milestone 2 is a hard gate, not a target date. If
either specialist review is delayed, the pilot delays with it.
