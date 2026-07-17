# Clarifications for MiniMoney — v18

> User decisions resolving all seven required changes from the Investment
> Committee's third review (Verdict_v3.md, "Proceed with Changes").
> Gathered methodically, one item at a time, by the Chief of Staff at the
> user's request so none were missed. Not a pivot. To be incorporated
> into BusinessCase_v18.md alongside Verdict_v3.md.

## Date
2026-07-09

## Required change 1 — the six specialist design recommendations, all
## now decided

1a. **Terminology — ADOPTED as recommended.** Debt-coded language
("invoice," "arrears," "late penalty") is reserved for parent-facing
surfaces only. Child-facing surfaces use softer language ("payslip"
stays; "arrears"/"penalty" wording never appears on the child's side).
Directly implements the legal opinion's mitigation for the case's single
highest-optics-risk item.

1b. **Exam-bonus mechanic — HYBRID redesign, user's own variant
(verbatim): "Reward behaviours while providing a Bonus for that
translating into improved results. Rewards will still be given for the
effort but bonus rewards for improved results."** The primary reward now
targets controllable behaviors (effort: study time, homework
completion), per the child-development review's recommendation, with a
secondary bonus layer retained for improved results. This is a partial
adoption: the behavior-primary structure follows the evidence (Fryer/
NBER: inputs work, outputs don't), while the retained outcome-contingent
bonus layer means the intrinsic-motivation risk identified by Deci/
Koestner/Ryan is reduced but not fully removed. The Incubator should
document this as the user's deliberate design choice, characterizing
honestly which part follows the specialist evidence and which part
retains a known, accepted residual risk.

1c. **Late-penalty mitigation — ADD a grace-period/pre-escalation
reminder mechanism.** The user chose the reviewer's first option
(reduce trigger frequency at the source) over pilot-measurement-only.
Design specifics (grace period length, reminder cadence) are not yet
specified — the mechanism is committed, its parameters are a build-spec
detail.

1d. **Fintech Advance — ADOPTED as recommended.** The module will NOT
use MiniMoney's existing Mpoints/badge gamification for the
trading-education content itself; presentation leans toward risk
literacy rather than aspirational framing, per the child-development
review.

1e. **Curriculum — three-tier age framework ADOPTED as recommended**
(roughly 6-9 softened task/reward framing, 10-14 basic transactional
literacy, 15-18 pre-employment literacy), replacing the previous
single-metaphor direction. Note: the Incubator should reconcile this
three-tier framework against the product's existing six-way age
sub-bands (6, 7, 8, 9-10, 11-14, 15-18) — the Investment Committee's
Risks/Assumptions list flagged this reconciliation as not yet done.

1f. **Pilot measurement — full recommended package ADOPTED**: borrowed
items from the Parenting Stress Index–Short Form and Family Assessment
Device (General Functioning Scale), within-family/within-week
penalty-trigger-vs-mood correlation tracking, age-stratified results,
and a child-report instrument (Child–Parent Relationship Scale,
Conflicts subscale) alongside parent-report.

**Sequencing note per the Investment Committee's requirement:** items
1b and 1c are decided now, before any family enrolls in the pilot — the
Committee's condition that these two specifically be resolved
pre-enrollment is satisfied at the decision level (build implementation
follows).

## Required change 2 — subscriber-count discrepancy and family-vs-child
## ambiguity: RESOLVED

**The funnel's unit is per FAMILY (verbatim decision: per family).**
One subscription = one family = up to 4 children. All install,
subscriber, and revenue figures throughout the case should be restated
on a per-family basis. This resolves the 180-1,830 vs. 360-2,440
discrepancy — the Incubator should recompute the funnel on the
per-family basis and state plainly which of the previously-cited ranges
(if either) survives the correction.

## Required change 3 — regulatory recheck ownership and fallback:
## RESOLVED

**Owner: the user personally owns both rechecks** (SARB/NPS Act for
account-linking; FPB classification for Mpoints). **Timing: build-spec
stage** — the same trigger already established for the specialist legal
opinion (once a stable working model exists, before pilot testing with
real families).

**Fallback decisions, both explicit:**
- If the SARB/NPS Act question is unresolved by launch: **launch
  without account-linking** (it is optional anyway; add later once the
  open-banking framework is finalized).
- If the FPB classification question is unresolved by launch: **launch
  without Mpoints** (per the Investment Committee's escalation of this
  item — the user accepts shipping without the cosmetic-rewards
  gamification loop rather than shipping it unclassified). The Incubator
  should trace what a no-Mpoints launch configuration means for
  dependent features (the in-app cosmetic store, the flat 10-Mpoints-
  per-task reward, Google Play Families Policy loyalty-point disclosure
  item) — a real ripple-effect check per Playbook Entry 2, not a
  footnote.

## Required change 4 — unverified legal citation: EXTERNAL ACTION,
## PENDING

Verification of the flagged case citation (Conradie v Rossouw pinpoint
reference) goes back to the retained lawyer directly. Not blocking any
other item; remains open until the lawyer confirms. The Incubator should
carry this as a named open item, not silently drop it.

## Required change 5 — curriculum workstream timing: RESOLVED

**Parallel, starting now** — curriculum content authoring runs alongside
the engineering build, not after it, per the Investment Committee's
requirement. (Note: CurriculumDraft_v1.md exists as Incubator-drafted
candidate content from an earlier prep task; the user has not yet
reviewed/adopted it. It is available as a starting point for this
workstream but is not part of this Business Case revision's inputs.)

## Required change 6 — pilot validation scope: RESOLVED, with a caveat
## to document honestly

**The pilot will validate BOTH mechanic safety/child-development signal
AND market demand** (user's explicit choice of the double-duty option).
The Incubator should document this decision alongside the
child-development reviewer's own stated caution that a 20-50 family
pilot is underpowered for statistical validation — i.e., demand findings
from this pilot will be directional/qualitative, not statistically
validated, and recruitment design must now serve both goals. This is a
user decision made with the limitation known, not an oversight.

## Required change 7 — cost/runway: RESOLVED (verbatim from user)

"Total budget im willing to commit is R10 000 for the development of
the app. For opinions and advise, i have a policy that i can use to get
those advices which is a zero cost to the app. I can sustain this for 6
months before needing funding."

Structured:
- **Development budget: R10,000 total** committed for the app build.
- **Professional opinions/advice: zero marginal cost to the venture** —
  the user holds a policy (insurance/legal-benefit) through which
  legal and similar professional advice is obtained at no cost to the
  app. (This also retroactively explains how the specialist legal
  opinion was obtained without the previously-scoped R25,000-R80,000
  spend.)
- **Runway: 6 months** at current commitment before external funding is
  needed.

The Incubator should reconcile the R10,000 development budget honestly
against the case's previously-cited $25,000-$120,000+ agency
engineering-cost range: the solopreneur/AI-assisted build model was
always the stated approach (agency figures were a reference frame, not
the plan), but the gap between R10,000 (~$550) and even the lowest
agency-tier figure is now concrete and should be stated plainly as the
case's execution-capacity risk — the budget effectively prices in the
founder's own unpaid labor plus AI-assisted development, with R10,000
covering incidentals/tooling/external help, and the 6-month runway is
the real constraint. Do not smooth this over; state it as the
Investment Committee would want to see it.
