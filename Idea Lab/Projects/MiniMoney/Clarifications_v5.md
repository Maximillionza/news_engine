# Clarifications for MiniMoney — supplied after Incubator v4 gate failure

> These are additional facts supplied by the user in response to specific
> gaps flagged in BusinessCase_v4.md. This is not a pivot — the original
> premise is unchanged. Treat these as authoritative additions to the
> case study, to be incorporated into BusinessCase_v5.md.

## Date
2026-07-06

## Raw clarification (verbatim from user)

collapse everything behind parental consent,

Operations and Constraints
task assignment/verification method
Before any tasks are assigned, parents are asked to submit a budget. This budget is what the basic income will be for the minor. Any additional tasks not assigned as part of this basic agreement will earn additional Mbucks(in app currency).
The budget is used to assign a predefine rate per task based on the budget. If the minor earns 100 mbucks per month and the task is to sweep at an earn rate of 1%, the minor will earn 1 Mbuck

This is can be amended and a fixed number inserted vs a %
for completing a task the minor can earn 10 Mpoints per completed task. The Mpoints are the only currency that can be spent in the in app store. Mbucks is the virtual currency that mimics the actual currency that will be paid to the minor e.g 10 Mbucks = R10. The minimum per task is 1 Mbuck.

There will be predefined tasks and grouped them by type. These can be assigned to the Minor by the parent
Should a task not exist, the parent can manually create a task and then set an agreed rate
Tasks can be recurring dependent on when the task needs to be completed. Monthly, weekly, daily.
Bonus points can be earned during exam period where the parent can assign a Mbuck value as n incentive. Example: the minor has 6 subjects averaging 65%. For every increase of 5% they earn 5 Mbucks upto a maximum of 15 Mbucks for anything 15% or higher

Once a task has been completed, the minor then marks it as complete and the Parent gets a notification of the completed task
a weekly report it provided with an overview of what tasks was completed to both Parent and Minor.
Parents can make it a requirement for certain tasks to be marked complete after submitting a photo which opens the Camera app directly and does not allow for pretaken photos to be submitted. The pupose is to foster trust so the parent can decide which tasks if any needs proof.

Should the parent disagree that a task has not been completed, they can decline the completed task. This needs to be done within 48 hours of the task being marked complete to avoid last minute disputes before payment is due.
Should a dispute arise, the parent and minor need to compromise. (a later feature to be added is an in app mediator powered by AI)

Payment by the parent would in most instances be seamless as the expectation is the minor would earn a set rate monthly and the parent can therefor have a recurring payment set up. Should there any increase in payment, this is can be made as an extra payment. The Parent will then mark the payment as complete and the minor will accept or dispute that payment was made. This is a feature that cant be strictly enforced until payment be routed through the app. Should the payment not be marked as complete there is a late penalty that will be incurred at 5 Mbucks per week of delay which is part of the conditions when setting up the budget that the parent needs to agree to. If a month past the rate increases to 6 per week eventually capping at 10 per week. This is added to each statement as a remaining arrears to be paid is is visable to the parent and minor

The primary platform is Android but future development is to port it to IOS

rough budget/timeline, platform choice)

## Relevant to which BusinessCase_v4.md gaps

- **Legal & Compliance / Child Data & Consent (Critical, Partial, central
  open question was the education-only direct-signup carve-out)**: user
  resolves the open question by explicitly choosing their own stated
  fallback — collapse everything behind parental consent. There is no
  longer an education-only direct-signup mode; a minor cannot access ANY
  part of the app, including education content, without a pre-existing,
  consenting parent account. This directly closes the single most urgent
  open question flagged in v4.

- **Operations (Incomplete across all four prior versions)**: comprehensively
  addressed for the first time. Key mechanics supplied:
  - A parent-submitted **budget** precedes any task assignment and sets
    the minor's "basic income."
  - Two distinct in-app currencies are now named: **Mbucks** (real-money-
    pegged, e.g. 10 Mbucks = R10, used for the earnings/payslip/invoice
    mechanic) and **Mpoints** (10 earned per completed task, spendable
    only in the in-app cosmetic store) — this directly resolves the v4
    "dual-currency naming collision" risk, since the two systems now have
    distinct names rather than both being called "points."
  - Task earn-rate can be a percentage of the budget (e.g. 1% of a 100
    Mbuck/month budget = 1 Mbuck per task) or a fixed Mbuck amount,
    parent-configurable either way. Minimum 1 Mbuck per task.
  - Predefined tasks exist, grouped by type, assignable by the parent;
    parents can also manually create custom tasks with an agreed rate.
  - Tasks can recur monthly, weekly, or daily.
  - A bonus mechanic exists tied to academic performance during exam
    periods: parent assigns a Mbuck incentive scaled to improvement in
    average grade (e.g. every 5% improvement across 6 subjects earns 5
    Mbucks, capped at 15 Mbucks for a 15%+ improvement).
  - Task completion flow: minor marks a task complete, parent is
    notified; a weekly report summarizing completed tasks goes to both
    parent and minor.
  - Parents can require photo-proof for specific tasks; the photo must be
    taken live via a direct camera-app launch (no pre-taken/gallery
    photos accepted) — described purpose is fostering trust, applied
    selectively per task at the parent's discretion.
  - Dispute mechanism: the parent can decline a marked-complete task
    within a 48-hour window (to avoid last-minute disputes before
    payment is due). Beyond that, "the parent and minor need to
    compromise" — no formal resolution mechanism is described. A future
    (not current-scope) AI-mediator feature is noted as a later addition.
  - Payment confirmation mechanism (previously unresolved since v2):
    parent marks the payment as complete; the minor then accepts or
    disputes that the payment was actually made. The user explicitly
    acknowledges this cannot be strictly enforced unless/until payment is
    routed through the app itself (it currently is not — payment happens
    via the parent's own banking app, per `Clarifications_v2.md`). A late
    penalty applies if payment is not marked complete: 5 Mbucks/week of
    delay, escalating to 6 Mbucks/week after one month, capping at 10
    Mbucks/week — agreed to by the parent as a condition of the initial
    budget setup. Outstanding arrears are shown as a running line item on
    statements visible to both parent and minor.

- **Constraints (Incomplete across all four prior versions)**: platform
  choice now supplied — primary platform is Android, with iOS porting
  planned as future work, not part of initial scope. No budget, timeline,
  or team-size figures were supplied for the business/build itself (the
  "budget" described above is an in-product parent-to-child budgeting
  feature, not the company's development budget — these are distinct
  concepts and should not be conflated).
