# Structural Enhancements — Idea Lab Framework

> This is NOT case content. It tracks observations about the Idea Lab
> **framework itself** — its templates, gates, routing rules, and
> subagent instructions — surfaced while running actual case studies.
> Nothing here is auto-implemented. Per the user's instruction, this list
> is reviewed once a project has gone through its full lifecycle, not
> acted on mid-case. Entries are proposed observations, not decisions.

## How to use this file
- Add an entry whenever a case study surfaces something about the
  *framework's own design* (not the case's content) worth reconsidering
  — a gate that doesn't test what it claims to, an undefined routing
  edge case, a rubric that produces a misleading signal, a recurring
  process gap.
- Each entry: **Date**, **Source** (which case/stage surfaced it),
  **Observation**, **Candidate enhancement**, **Status**.
- Status starts at `Open`. On review, the user marks it `Deferred`
  (still valid, not yet worth building), `Approved` (build it), or
  `Rejected` (not worth it, with a one-line reason so it isn't
  re-proposed from scratch later).
- This supersedes the two items previously listed inline in this
  project's `CLAUDE.md` under "Future Enhancements" — they are carried
  forward below as Entries 1 and 2. `CLAUDE.md` now points here instead
  of listing them directly, to avoid the two drifting out of sync.

---

## Entries

### 1. Portfolio/Meta Observer
**Date identified:** Pre-existing (carried forward from `CLAUDE.md`)
**Source:** Framework design discussion, prior to any case study
**Observation:** No mechanism currently exists to spot patterns *across*
multiple case studies (reused assumptions, recurring gaps, experts
repeatedly assembled) — every case runs in isolation by design.
**Candidate enhancement:** A Portfolio/Meta Observer operating across
`Projects/`, not within one case, surfacing cross-case patterns.
**Status:** Open — explicitly not worth building until several case
studies have actually completed; no portfolio exists yet to observe.

### 2. Framework Auditor
**Date identified:** Pre-existing (carried forward from `CLAUDE.md`)
**Source:** Framework design discussion, after Research House's original
"no memory, ever" rule was found to directly contradict the later
engagement-log continuity request — caught manually by the user, not by
any mechanism.
**Observation:** Nothing currently checks `CLAUDE.md` and the
`.claude/agents/*.md` files for internal contradiction before they
surface in a live run.
**Candidate enhancement:** A Framework Auditor that reviews the
framework's own instruction files for contradictions before they cause a
mid-run problem.
**Status:** Open — was unproven after a single incident at the time it
was first listed. MiniMoney's run surfaced at least one further data
point relevant to this (Entry 5 below, the Gate Integrity Check's
format-vs-substance finding) — worth weighing together at next review,
not necessarily still "a single incident."

### 3. No case state for "blocked on external-world action" distinct from
"needs another writing cycle"
**Date identified:** 2026-07-09
**Source:** MiniMoney, Investment Committee v2 (re-review of
BusinessCase_v15.md)
**Observation:** The routing table's only response to an Investment
Committee "insufficient context" verdict is "Return to Incubator with
specific gaps." MiniMoney's second Investment Committee review explicitly
stated that its blocking gaps (a specialist legal opinion, a
child-development expert review, actual authored curriculum content)
cannot be resolved by *any* further Incubator writing or Research House
desk-research cycle — they require the user to go obtain real-world
inputs. The framework has no distinct state for this; the only available
routing path (back to Incubator) implies another writing cycle is the
right next step, which in this situation it explicitly is not.
**Candidate enhancement:** A distinct case state (e.g. "Paused — Pending
External Action") that the Chief of Staff can set when a verdict
identifies blockers requiring real-world action rather than more
documentation. The case stays paused — no further Incubator/Investment
Committee cycling — until the user confirms specific named inputs have
actually been obtained, at which point normal routing resumes.
**Status:** Open.

### 4. Investment Committee (and Developing Committee) output versioning
is undefined
**Date identified:** 2026-07-09
**Source:** MiniMoney, second Investment Committee delegation
**Observation:** The Versioning section of `CLAUDE.md` only explicitly
covers Business Case revisions ("every return-to-Incubator cycle
increments the version"). It says nothing about whether `Verdict.md` /
`FullReview.md` should be versioned or overwritten when a case re-enters
Investment Committee review multiple times. The Chief of Staff made an
ad hoc call this session (versioning as `Verdict_v2.md`/
`FullReview_v2.md`) without an explicit rule to follow.
**Candidate enhancement:** Extend the Versioning section of `CLAUDE.md`
to explicitly state the versioning convention for Investment Committee
and Developing Committee outputs, not just the Business Case.
**Status:** Open.

### 5. Completion gate criteria for Expert Roster / Devil's Advocate are
format-based, not substance-based
**Date identified:** 2026-07-09
**Source:** MiniMoney, Investment Committee v2, Mandatory Gate Integrity
Check
**Observation:** The Incubator's self-certification checks "roster
entries ≥3 sentences, each naming a specific case-study assumption" and
"Devil's Advocate objections ≥3, each citing a specific section" — both
purely structural/format tests. A roster entry or objection can satisfy
sentence-count and citation requirements without being probing or
well-reasoned. The Investment Committee, by design, cannot check
substance either (it never reads these files). Nothing in the pipeline
currently verifies these artifacts are *good*, only that they are the
*right shape*.
**Candidate enhancement:** Related to Entry 2 (Framework Auditor) but
narrower — could be addressed by that broader mechanism, or by a
lighter-weight periodic substance spot-check (e.g. the Chief of Staff or
user occasionally samples actual roster/Devil's Advocate content against
a quality rubric, independent of the Investment Committee's isolation,
which must remain intact for its own review).
**Status:** Open.

### 6. No mechanical check on the Readiness Score's own arithmetic
**Date identified:** 2026-07-08 (bug found), documented here 2026-07-09
**Source:** MiniMoney v8 — Incubator caught a denominator error inherited
from v7 (points-possible assumed 3 double-weighted Critical sections;
only 2 exist in the table). The error had already persisted through at
least one prior version before being caught, by the Incubator itself,
not by any check.
**Observation:** The Readiness Score table is hand-computed by the
Incubator each cycle with no independent verification step (e.g.
confirming stated points-possible actually equals count-of-★-sections×2
+ count-of-non-★-sections, times the per-status point values).
**Candidate enhancement:** A simple mechanical self-check the Incubator
runs against its own Readiness Score table every cycle, flagging any
arithmetic inconsistency before it ships in a version, rather than
relying on the next cycle happening to notice.
**Status:** Open — low-effort, low-risk fix; could reasonably be folded
into the Incubator's own agent instructions directly rather than waiting
for a broader review.

### 7. Readiness Score weights Status only, not Confidence
**Date identified:** 2026-07-09
**Source:** MiniMoney, Incubator Playbook Entries 3 and 4 (Confidence
trajectory as its own signal; rising Confidence ≠ better news)
**Observation:** Two playbook lessons this case produced both work
around the same underlying rubric limitation: the Readiness Score is
computed purely from Status (Complete/Partial/Incomplete), so a
section's Confidence can erode or recover across many revisions with
zero effect on the score. The playbook lessons are good mitigations
(surface Confidence trajectory explicitly), but they're a workaround, not
a fix to the rubric itself.
**Candidate enhancement:** Reconsider whether the Readiness Score formula
should incorporate Confidence as a weighting factor (e.g. a "Partial,
High confidence" section scoring higher than a "Partial, Low confidence"
section), rather than treating Confidence as purely narrative context
alongside a Status-only score.
**Status:** Open — flagged as a bigger, more disruptive change than
Entry 6; would need careful design (a Confidence-weighted score changes
what the 70% threshold has historically meant) before adopting, not a
quick fix.

### 8. Business Case document format — unified vs. split, and inline
verbosity
**Date identified:** 2026-07-09
**Source:** MiniMoney, user question after noticing sections referencing
resolutions with no content in the section itself (later found to be a
distinct, more serious defect — see Playbook Entry 5 — not primarily a
verbosity issue)
**Observation:** The user asked whether the Business Case should be
split into a "clean" business document plus a separate
assessment/provenance document, given how much inline "per
Clarifications_vN.md" / "Resolved this revision" commentary accumulates
per section across many revision cycles. The Chief of Staff recommended
keeping the document unified (the inline Status/Confidence/Evidence tags
and citations are load-bearing for Investment Committee and Developing
Committee traceability, not decorative) and instead proposed tightening
inline citations to a compact form, with fuller narrative confined to
the top-of-document changelog block and `01_ChiefOfStaff_Log.md`. The
user chose to leave the format as-is for now, deferring the tightening
proposal too.
**Candidate enhancement:** If unified-document verbosity becomes a
recurring friction point across multiple case studies (not just this
one), revisit the compact-citation-format proposal as an update to the
Incubator's own agent instructions.
**Status:** Deferred (by user, 2026-07-09) — revisit only if this
recurs on a future case, not proactively.

### 9. No independent check on the Incubator self-grading its own
Status/Confidence upgrades — now a three-cycle recurring pattern
**Date identified:** 2026-07-09 (raised at v16, escalated at v17)
**Source:** MiniMoney, Incubator v16 and v17. This case's own Devil's
Advocate raised a self-grading concern in three consecutive cycles (the
transcript itself notes this as "Pattern Continuity" at v17): v16
Objection 2 (Confidence upgrades graded by the same body that performed
the underlying restoration), and v17 Objection 3 (the Readiness Score
landing at exactly 91/130 = 70.0% — precisely the completion-gate
threshold, not merely above it — after six discretionary Status
upgrades in one cycle, several of which the Devil's Advocate itself
argues admit a stricter, equally-defensible reading that would have
landed below threshold).
**Observation:** Every Status, Confidence, and Evidence tag in every
Business Case — including whether the completion gate itself passes —
is assigned by the Incubator, in the same cycle it produces the
underlying content those tags describe. Nothing in the pipeline
independently re-checks that self-assessment before the score is
reported to the user or before a "gate passes" verdict would trigger
auto-advancement to Investment Committee. This is directly related to
Entry 5 (format-based, not substance-based, gate criteria for Expert
Roster/Devil's Advocate) but is broader: it applies to the Readiness
Score itself, the single number this entire framework's advancement
logic hinges on.
**Candidate enhancement:** Some form of independent verification step
before a Business Case's self-certified "gate passes" is treated as
final — options worth weighing at review, not decided here: (a) a
lightweight second-pass review (by a fresh Incubator instance with no
memory of having produced the content, or a distinct reviewing role)
specifically re-grading Status/Confidence/Evidence tags against the
document's own text before the score is reported; (b) treating a score
landing within some margin of the 70% threshold (not just above it) as
automatically warranting the kind of manual scrutiny this test period
already requires for a *failing* gate — i.e., "just barely passed" gets
the same human attention as "failed," not less; (c) folding this into
whichever mechanism eventually addresses Entry 2 (Framework Auditor) or
Entry 5, since all three are instances of the same underlying gap: this
framework asks a subagent to grade its own work with no check.
**Status:** Open — escalated in urgency by the third consecutive
occurrence and by the exact-threshold landing, which is a more
concrete, higher-stakes instance than the two prior Confidence-only
occurrences.

### 10. Playbook lessons alone did not prevent a third recurrence of
the same section-thinning defect
**Date identified:** 2026-07-09
**Source:** MiniMoney, v18. This case's own Devil's Advocate (Objection
6) caught Market & Competition degrading a third time: fully restored
at v16 (Entry 6's fix), reduced to a bare cross-reference at v17, then
rebuilt at v18 from only v17's (already-thinned) content, since v16 was
not among that cycle's authorized inputs.
**Observation:** Playbook Entries 5 and 6 were written specifically to
prevent this class of defect, and were presumably read by the Incubator
at the start of the v17 and v18 engagements (per standing instruction,
every Panel reads its playbook once at the start of each engagement).
The defect recurred anyway, because the actual *delegation scope* for a
routine revision cycle (v17→v18) only included the immediately prior
version as an input, not enough history to notice or prevent thinning.
A playbook lesson can tell the Incubator what to watch for, but cannot
give it access to files the Chief of Staff didn't include in that
cycle's delegation — the lesson and the delegation's actual input scope
are two different levers, and only fixing the first (Entries 5/6) while
leaving the second unchanged (routine cycles still get just N-1) did
not close the gap.
**Candidate enhancement:** Either (a) routine revision delegations
should default to including more than just the immediately-prior
version for sections with a known thinning history, not just during
dedicated consolidation passes; or (b) the Incubator's own standing
instructions should require an explicit self-check per revision —
before finalizing, compare each section's length/specificity against
the previous version and flag any section that shrank without a stated
reason — independent of whether the current delegation happens to
include enough history to trace the cause. Option (b) is more robust
since it doesn't depend on the Chief of Staff remembering which
sections have a thinning history when scoping each delegation.
**Status:** Open — directly related to Entries 5 and 6, but a distinct
finding: those two lessons address *recognizing* thinning; this one is
about *preventing recurrence* when the recognizing party doesn't have
the input access to apply the lesson.

**Update, 2026-07-14 (post-Developing-Committee handoff):** a fourth
instance was found, in Operations, only after this case had completed
its full pipeline and reached the build stage — the Developing Committee
declined to assume a mechanic existed rather than guess, which surfaced
that Operations had silently lost its percentage-of-budget task-rate
detail starting at v6, never restored even by the dedicated v15/v16
consolidation pass. The reason it evaded that pass specifically: Entry
10's original candidate enhancement (b) — comparing section length/
specificity against the previous version — would not have caught this
one either, because Operations' *Status tag* never changed (it stayed
"Complete" throughout), even though its *content* thinned underneath
that unchanging tag. A length/specificity self-check would need to run
on every section regardless of whether its Status tag looks stable, not
be triggered by a Status change or a "flagged as thin" heuristic — the
whole point of this recurrence is that nothing about the section's
visible metadata signaled a problem. This raises the bar for candidate
enhancement (b): the self-check needs to be unconditional per revision,
not a targeted check on sections already suspected of thinning.

### 11. Routing table has no distinction between viability-blocking and
execution-detail "proceed with changes" required items
**Date identified:** 2026-07-09
**Source:** MiniMoney, after seven consecutive Investment Committee
"proceed with changes" verdicts (v8, v17, v18, v20, v21, and v23's
round). The user directly questioned whether the pattern was "stalling
the build" on items that were project-management/execution-detail in
nature rather than core business-viability blockers.
**Observation:** The routing table currently treats every "proceed with
changes" verdict identically: "Return to incubator with Verdict.md
attached. Version ticks. Re-enters Investment Committee — does NOT skip
to Developing Committee." This is true regardless of whether the
required changes challenge the business's fundamental legal, ethical, or
strategic viability, or are execution-detail refinements (a P&L model,
confirming the founder's own age, naming acquisition channels) that the
Investment Committee itself, in its own verdict language, characterized
as not challenging viability ("this is not a case of missing context,"
"the legal and regulatory foundation is genuinely solid"). On review of
round 7's specific six items, the Chief of Staff and user agreed five of
six were execution-detail, not viability-blocking — but the routing
table offered no mechanism to route them to Developing Committee (whose
explicit job is exactly to keep such items traceable during execution
planning) without first cycling through another full Incubator/
Investment Committee round, or without an ad hoc, manually-negotiated
deviation from the table's literal instruction.
**Candidate enhancement:** Extend the Investment Committee's verdict
format (or the routing table itself) to optionally distinguish
"required changes affecting viability" from "required changes that are
execution-detail/traceability items" within a single "proceed with
changes" verdict — allowing the latter category to route directly to
Developing Committee with the items explicitly carried forward as
traceability obligations, while the former category still requires
another Incubator/Investment Committee cycle. This would formalize what
this case did ad hoc (an explicit, logged, user-authorized deviation)
into a repeatable, framework-supported path, rather than requiring a
manual override each time the pattern recurs.
**Status:** Open — first observed after seven rounds on one case; worth
confirming this generalizes (rather than being specific to MiniMoney's
unusually long iteration history) before treating it as validated.

---
