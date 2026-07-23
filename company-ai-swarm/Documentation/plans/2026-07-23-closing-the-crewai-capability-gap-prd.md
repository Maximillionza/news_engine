# PRD: Closing the Capability Gap with CrewAI

**Status:** Superseded for status-tracking purposes by `IMPLEMENTATION_PLAN.md`'s "Phase 12
and beyond" section (added 2026-07-23) - initiatives 5.2/5.3/5.4 below now live there as
Phases 12/13/14, with the same acceptance criteria. This document's reasoning and evidence
stay valid and are referenced from there; check `IMPLEMENTATION_PLAN.md` for current status
rather than this file, so status isn't tracked in two places.
**Date:** 2026-07-23
**Author context:** Follows a direct architecture comparison against CrewAI (hierarchical
multi-agent OSS framework). The orchestration/governance layer came out ahead; this document
scopes the areas that didn't.

## 1. Context

A dimension-by-dimension comparison against CrewAI found The Company ahead on orchestration
hierarchy (Department Head triage vs. CrewAI's single flat manager), governance (a formal
four-condition escalation policy + Decision Records vs. CrewAI's single `human_input=True`
primitive), and execution model (a real async objective queue vs. CrewAI's synchronous
`kickoff()`). It found CrewAI ahead on tool ecosystem, provider breadth (via LiteLLM), and -
most importantly - production-proof: CrewAI has thousands of independent users finding its
edge cases; The Company has one operator and a passing test suite, which is necessary but not
sufficient for the same confidence.

This document scopes what's actually worth building to close the gaps that are real and
worth closing, and explicitly excludes the ones that aren't.

## 2. Current-State Findings (grounded, not estimated)

- **[Certain] No tool-calling capability exists for any agent.** No `tool`-named file or
  directory exists anywhere in the repo. `AgentSDKModelProvider.__init__`'s `allowed_tools`
  parameter defaults to `()` everywhere it's constructed, and its own docstring states tools
  are only meant to be passed for agents "meant to act on the local machine" - meaning today,
  every department agent reasons over a prompt and produces text. A Research Agent cannot
  search the web; a Compliance Agent cannot look anything up.
- **[Certain] Zero performance or simulation tests exist.** `Tests/performance/` and
  `Tests/simulation/` are both scaffolded, empty directories - 0 test files in either, despite
  correctness being well-covered elsewhere (28 integration tests, 13 passing MVS acceptance
  tests covering all 10 of `IMPLEMENTATION_PLAN.md` Phase 9's categories). Nothing proves
  behavior under concurrent load, or that the technical-failure escalation path (Phase 8)
  actually fires correctly when a provider call fails mid-workflow rather than in a
  hand-constructed unit test.
- **[Likely] No real (non-test) usage has accumulated.** No evidence of usage logs or
  Historical-tier memory content beyond what tests themselves write. The escalation policy
  and memory-promotion logic are proven correct against test scenarios the author wrote,
  which is a different, weaker claim than "proven correct against objectives the author
  didn't anticipate" - the thing CrewAI's user base provides for free.
- **[Certain] `IMPLEMENTATION_PLAN.md` is stale and actively misleading.** It states "No code
  has been written against this plan," while `services/orchestrator`, `services/
  workflow_engine`, `services/shared/providers/{agent_sdk,anthropic}_provider.py`, and
  `apps/api_gateway/objective_queue.py` all exist, are tested, and match the *already
  implemented* architecture `SDK_MIGRATION_PLAN.md` describes. Any future planning session
  (human or agent) reading `IMPLEMENTATION_PLAN.md` cold will misjudge what phase this project
  is actually in.

## 3. Goals

Close the gaps above to the extent they matter for a single-operator personal swarm - not to
match CrewAI feature-for-feature as a general-purpose product.

## 4. Non-Goals

- **Provider breadth (LiteLLM-style multi-vendor support).** CrewAI supports dozens of model
  vendors "for free" via LiteLLM; The Company's two-provider `ModelGateway` (Anthropic API
  key + Claude Agent SDK/subscription) is a deliberate choice per `SDK_MIGRATION_PLAN.md`
  Section 1's personal/single-Director billing model, not an oversight. Only revisit this if
  there's a concrete reason (cost, redundancy) to want a second model vendor - don't chase it
  as a default.
- **Community/ecosystem parity.** Not achievable or wanted for a single-operator system.
  Excluded entirely.

## 5. Proposed Initiatives

### 5.1 Fix the planning-doc drift (do this first)

**Problem:** `IMPLEMENTATION_PLAN.md`'s stated status contradicts the repo's actual state,
making it an unreliable source of truth for what to build next.

**Work:** Reconcile `IMPLEMENTATION_PLAN.md`'s phase statuses against what's actually
implemented and tested (Phase 9's MVS acceptance suite passing is strong evidence Phases 0-9
are substantially done - verify precisely which deliverables, if any, within those phases are
still missing) - or explicitly mark it superseded by `SDK_MIGRATION_PLAN.md` plus this
document, if that reflects reality better.

**Acceptance criteria:** `IMPLEMENTATION_PLAN.md`'s phase-completion claims match what a grep
of the repo shows. This document gets revisited before it suffers the same drift.

**Priority:** Low effort, do first - every other initiative below is easier to scope
correctly once "what phase are we actually in" has one honest answer.

### 5.2 Give agents real tools

**Problem:** No department agent can act beyond generating text from a prompt. This is the
single largest functional gap versus CrewAI, and arguably the largest gap versus the swarm's
own stated purpose - a Research Agent that can't research anything external is a limited
Research Agent.

**Work:** The cheapest path is also the correct one: `AgentSDKModelProvider` already has a
working `allowed_tools` mechanism wired straight into the Claude Agent SDK's own tool loop -
it has simply never been populated. Start narrow, matched to each department's actual mission
(per `departments/*/definition.yaml`):
- Research: a web-search tool.
- Engineering: a sandboxed code-execution or lint/test-runner tool.
- Compliance: a policy/document-lookup tool.
Do not build a general-purpose tool library up front (that's CrewAI's `crewai-tools` scope,
and a non-goal here) - wire one real tool per department, prove it end-to-end, then expand
only where a real objective actually needed a tool the agent didn't have.

**Acceptance criteria:** At least one department agent completes a real objective that
requires an external tool call mid-reasoning, and that tool call is visible in the existing
telemetry sink (`observability_service/telemetry.py`) - not just inferable from the final
text output.

**Priority:** High.

### 5.3 Prove failure and load behavior, not just correctness

**Problem:** Correctness is well-proven (13/13 MVS acceptance tests passing). Nothing proves
the system degrades correctly under the conditions `SDK_MIGRATION_PLAN.md` itself already
flags as real risks - concurrent objectives competing for a shared subscription usage window
(Section 1, caveat 3), or a provider call failing mid-workflow.

**Work:** A small, targeted suite - not full Phase 11 simulation scope:
1. N concurrent objectives through `queue_worker.py` - confirm no queue corruption, no lost
   or duplicated jobs.
2. A forced provider failure mid-workflow - confirm it produces the technical-failure
   escalation path Phase 8 already defines, distinct from the four framework-verdict
   conditions, and that this is independently reproducible (Phase 8's own exit criteria
   already claims this; this is where it actually gets proven).
3. One soak test running a realistic sequence of objectives over an extended period,
   confirming no resource leak or worker deadlock.

**Acceptance criteria:** Passing, committed tests for cases 1 and 2 at minimum. Case 3 documented
even if run manually rather than automated in CI.

**Priority:** High - directly de-risks a concern your own planning docs already named but
never tested.

### 5.4 Dogfood it

**Problem:** A passing test suite proves the system handles scenarios its author anticipated.
CrewAI's confidence comes from volume of usage nobody anticipated. That gap can't be closed
by writing more tests against your own assumptions - it closes by running real objectives
through the system and finding what breaks.

**Work:** Deliberately route a defined set of real personal objectives through the swarm over
several weeks. Review every Decision Record produced - not just whether the objective
succeeded, but whether the department routing, any escalation, and any memory promotion were
actually correct. Convert every mistake found into a new regression test.

**Acceptance criteria:** A running log of real (non-test) objectives processed, each with its
Decision Record reviewed, and at least one new regression test added per incorrect behavior
found.

**Priority:** Medium - low engineering effort, but consumes calendar time rather than
engineering time, so it should run in parallel with 5.2/5.3, not block on them.

## 6. Sequencing

1. **5.1** (docs) - cheap, unblocks everything else being scoped correctly.
2. **5.2** (tools) and **5.3** (failure/load testing) in parallel - both high-value, and
   neither depends on the other.
3. **5.4** (dogfooding) - start as soon as 5.2 lands enough tool capability to make real
   objectives worth running; continues indefinitely, not a phase with an end date.

## 7. Open Questions

- Is provider breadth (non-goal 4) actually a non-goal, or is there a concrete reason (cost,
  redundancy, a specific task better suited to a different model) to want a second vendor?
  Confirm before treating it as permanently excluded.
- What's the actual target cadence/volume for 5.4's dogfooding - a handful of objectives a
  week, or something heavier? This affects how much tool coverage 5.2 needs before dogfooding
  is worth starting.
