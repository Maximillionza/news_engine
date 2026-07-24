# Dogfooding Log

IMPLEMENTATION_PLAN.md Phase 14. A passing test suite proves the system handles scenarios
its author anticipated; it doesn't prove what an independent user base proves for free (see
`Documentation/plans/2026-07-23-closing-the-crewai-capability-gap-prd.md` Section 2 on why
this specifically matters here). This closes that gap the only way it can be closed: routing
real, non-test objectives through the swarm and reviewing what actually happened.

This phase has no code deliverable and no end date - what follows is the process and the log
itself, not something to be marked "complete."

## Why this can't be automated or run by the agent alone

Every other phase this session involved writing and testing code. This one is different on
purpose: the objectives have to be real (something you actually want done, not a contrived
test case), and judging whether the department routing, any escalation, and any memory
promotion were *actually correct* needs your judgment about your own business, not just
"did it return 200 and non-empty output." Same reason the live Agent SDK smoke test and the
`delete_task`/`forget_fact` confirmation-gate verification earlier in this project were
handed to you rather than run automatically.

## How to submit a real objective

Any of these reach the same `COOOrchestrator`:

- **Through Samaritan** (the natural, already-integrated path): ask Samaritan something that
  should route to The Company - `core/tools/company.py`'s `dispatch_to_company()` calls
  `POST /chat/sync` and relays the reply verbatim.
- **Directly via the dashboard**, if it's running.
- **Directly via the API**: `POST /chat/sync` (`{"message": "..."}`) or `POST /objectives`
  (`{"objective": "...", "required_output": "..."}`) with your `X-API-Key`.

## How to review one

1. Get the `decision_id` from the response (`/chat/sync` returns it directly; `/objectives`
   returns it as part of the outcome).
2. `GET /objectives/{decision_id}` for the Decision Record - `reasoning`, `chosen_action`,
   `agents_selected`, `outcome`.
3. Check three things, not just "did it work":
   - **Routing** - did it go to the department(s) it actually belonged to?
   - **Escalation** - if something should have escalated (per `orchestrator/escalation.py`'s
     four conditions) and didn't, or escalated when it shouldn't have, that's a finding.
   - **Memory promotion** - for anything that tripped an escalation, was it correctly held
     pending (`memory_service/promotion.py`) rather than silently promoted, or vice versa?
4. Log the entry below, whether it was correct or not - a clean run is still evidence, not
   just failures.
5. If something was wrong: file it as a real bug (same as any other finding this session),
   and write a regression test that would have caught it before considering it closed.

## Log

Fill in a row per objective reviewed. `Regression test added` is a file:test reference, or
`n/a` if the outcome was correct.

| Date | Objective (brief) | decision_id | Routing correct? | Escalation correct? | Memory promotion correct? | Regression test added | Notes |
|---|---|---|---|---|---|---|---|
| _(none logged yet)_ | | | | | | | |
