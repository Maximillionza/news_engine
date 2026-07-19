# Design: Department Head Triage (Phase 2 of Dynamic Model Selection)

**Status:** Implemented.
**Date:** 2026-07-19
**Relationship to Documentation/plans/2026-07-19-dynamic-department-routing-design.md:** that
spec's Section 6 listed this as the first of four deferred sub-projects, in dependency order
(Department Head triage -> dynamic agent/specialist selection -> token/cost budgets -> real
model tier selection). This document covers only Department Head triage. The other three
remain out of scope here and are carried forward to Section 6 below.

---

## 1. Problem Statement

Every `departments/*/definition.yaml` already carries a `leader` field (DOMS sec.5, Department
Object) - and DOMS sec.8-9 (Department Leadership / Department Leader Authority) describe real
responsibilities for that role: capability quality, agent performance, escalation, approving
department workflows. Today, `leader` is an empty string on all five departments, and
`orchestrator/department_registry.py`'s loader doesn't even promote it to a first-class field -
it falls into the catch-all `extra` dict. Nothing in the codebase reads it, and no entity
exists to act as one.

The practical consequence: once `COOOrchestrator.receive_objective()`'s classifier picks a
department, that department has no say in the matter. A department cannot say "this doesn't
actually belong to me, department X should handle it" or "this genuinely isn't worth spinning
up the swarm for." The COO's classification is final and unreviewed.

**Why this matters:** classification (Phase 1) is a single upfront judgment call about intent;
it can be wrong, and today there is no second opinion from the department actually being asked
to do the work - the same kind of review a real organization relies on a department lead for.

---

## 2. Scope

**In scope:**
- A real Department Head agent per department: registered identity, its own `agent.yaml`, its
  own `dispatch()`-driven triage call - not a bespoke lightweight call path.
- Two triage verdicts: Accept, or Reject-with-reasoning (reasoning may name a specific
  department the COO should try instead, or may say the objective isn't worth the swarm at
  all - both are the same verdict shape, distinguished only by whether a department is named).
- Single-department path: the COO retries once at a Head-suggested department (2 attempts
  total), then gives up.
- Multi-department workflow path: each department's Head evaluates its own assigned task
  immediately before that department's work dispatches, inside the existing sequential loop.
  A reject halts forward progress the same way a failed validation already does today - no
  rollback of already-completed departments' work, no reassignment attempted mid-workflow.
- Universal: this runs inside `receive_objective()` itself, so every entry point (`POST
  /chat`, `POST /chat/sync`, `POST /objectives`) gets the same triage gate - unlike Phase 1's
  sufficiency check, which was deliberately chat-only.
- A swappable dev/test default (`AutoAcceptDepartmentHead`), exactly parallel to
  `KeywordDepartmentClassifier` and `StubModelProvider`, so every existing test that
  constructs a `COOOrchestrator` keeps passing unmodified.

**Out of scope (future sub-projects, not designed here):**
- Dynamic agent count and specialist agent selection within a department.
- Token/cost budget management as a decision input.
- Real model tier selection.
- Reassignment retries inside the multi-department workflow path (a workflow's department list
  was already fixed by the classifier's decomposition; re-planning it mid-sequence is a
  materially harder problem left for later, if it turns out to matter in practice).
- Populating `department.manager` on individual agent `agent.yaml` files (a parallel, currently
  also-empty field) - out of scope unless it turns out to be needed for head-to-agent
  relationships.

---

## 3. Architecture

### 3.1 Data flow

```
receive_objective()
  1. classify_objective(...) -> ObjectiveClassification          [Phase 1, unchanged]
  2. Single-department path:
       attempt = 1
       loop (max 2 attempts):
         department = matched_departments[0] on attempt 1,
                      else the previous verdict's suggested_department_id
         verdict = head.evaluate(department, objective, ...)      [NEW - see 3.2]
         if verdict.accepted: break, proceed to Select Agents as today
         if attempt == 2 or verdict.suggested_department_id is None
             or suggested department unknown/already tried:
           -> DepartmentRejectedError (see 3.4)
         attempt += 1; retry with the suggested department
  3. Multi-department workflow path: inside execute_workflow()'s existing per-department
     loop, before select_agent()+dispatch() for each substantive department:
       verdict = head.evaluate(department, objective, ...)
       if not verdict.accepted: halt forward (same shape as today's validation-failure halt)
  4. Everything else (dispatch, decisions, escalations, learn) is unchanged.
```

### 3.2 `services/orchestrator/head.py` (new module)

```python
@dataclass
class HeadVerdict:
    accepted: bool
    reasoning: str
    suggested_department_id: str | None  # only meaningful when accepted=False

class DepartmentHead(Protocol):
    def evaluate(
        self, department: DepartmentDefinition, objective: str,
        agent_registry: AgentRegistry, model_gateway: ModelGateway,
        session: Session, coo_id: str, telemetry: TelemetrySink | None,
    ) -> HeadVerdict: ...

class AutoAcceptDepartmentHead:
    """Dev/test default - always accepts, zero calls, mirrors KeywordDepartmentClassifier's
    zero-network-call nature. Every existing test that constructs a COOOrchestrator without
    a `head` kwarg needs zero changes."""
    def evaluate(self, department, objective, **_) -> HeadVerdict:
        return HeadVerdict(accepted=True, reasoning="Auto-accept (dev/test default).",
                            suggested_department_id=None)

class LLMDepartmentHead:
    """Production: dispatches to the department's own registered head agent via the existing
    dispatch() (services/orchestrator/router.py) - the same AgentRuntime.execute_task() cycle
    research_agent_001's real work already goes through, not a bespoke model_gateway.generate()
    call like classification.py/intake.py use. This is deliberate: DOMS sec.8 makes the Leader
    accountable for escalation and agent performance the same way any other agent's work is
    accountable - triage should carry the same audit trail and permission checks, not a
    shortcut around them."""
    def evaluate(self, department, objective, agent_registry, model_gateway,
                 session, coo_id, telemetry) -> HeadVerdict: ...

def create_head_from_env(env: Mapping[str, str] | None = None) -> DepartmentHead:
    """DEPARTMENT_HEAD_TRIAGE env var: "auto_accept" (default) or "llm" - exactly parallel to
    DEPARTMENT_CLASSIFIER."""
```

`LLMDepartmentHead.evaluate()` looks up the head's `AgentDefinition` via
`agent_registry.get(department.leader)`, then calls the existing `dispatch()` with a task
framed as a verdict request, not a deliverable:

```python
result = dispatch(
    session, coo_id=coo_id, agent=head_agent, model_gateway=model_gateway,
    telemetry=telemetry,
    objective=(
        f"Evaluate whether this objective belongs to the {department.name} "
        f"({department.mission}): {objective}"
    ),
    required_output=(
        'Respond with ONLY a JSON object: {"accepted": true|false, "reasoning": "...", '
        '"suggested_department_id": "<id>|null"}'
    ),
)
verdict_data = json.loads(strip_code_fence(result.output))
```

`AgentRuntime`'s own validation (`agent_runtime/runtime.py:159`) only rejects *empty* output -
a short JSON verdict passes cleanly; no fight with the framework. `suggested_department_id` is
validated against the real registry and against departments already attempted in this
`receive_objective()` call before being trusted - a hallucinated or repeated ID is treated the
same as `null` (no valid suggestion), same discipline `LLMDepartmentClassifier` already applies
to hallucinated department IDs.

### 3.3 Agent registration

Each department that can actually be dispatched to gets a new
`agents/active/<dept>_head/agent.yaml` (4 files: research, engineering, compliance,
operations). Strategy is deliberately excluded - it has an empty `agents` list today, which
means the classifier already filters it out of `matched_departments` before anything reaches
triage (the same reason it has no worker agent). A Strategy head would never be invoked, so
building one is unnecessary work, not a completeness gap. Mission is explicitly triage, not
work product - e.g. research_head's mission: "Evaluate whether an objective genuinely requires
the Research Department's capabilities, or belongs elsewhere, or isn't worth the swarm at
all." `department.leader` is set to the head's identity ID (e.g. `research_head_001`) and
promoted from `extra` to a first-class field on `DepartmentDefinition`. If Strategy is ever
activated with real agents (out of scope here), it needs a head added at that time, same as any
new department per Section 3.6.

**Important:** the head's identity stays *out* of `department.agents`. That list is what
`allocator.py`'s capability-based `select_agent()` picks real work from - if the head were
listed there, it could accidentally get selected for substantive work it was never built to
do. The head is looked up directly by ID (`agent_registry.get(department.leader)`), never
through capability matching.

### 3.4 Rejection handling (`DepartmentRejectedError`)

A terminal reject (2-attempt cap reached, or a Head rejects with no valid suggested
alternative) writes a Decision Record and a new escalation condition, `DEPARTMENT_REJECTED` (in
`orchestrator/escalation.py`, alongside the existing five), then raises
`DepartmentRejectedError` - the same pattern `NoMatchingDepartmentError` already establishes,
which `dashboard_api.py` already treats as a normal completed reply, not an HTTP error. The
same `DEPARTMENT_REJECTED` condition covers both the single-department cap-hit case and the
multi-department mid-workflow reject case - one underlying event (a Head said no), reached via
two different paths, not two separate conditions for one cause.

### 3.5 Multi-department workflow integration

`workflow_engine/engine.py`'s `execute_workflow()` gets one new step inside its existing
per-department loop, immediately before `select_agent()`:

```python
for department in substantive_departments:
    verdict = head.evaluate(department, objective, agent_registry, model_gateway,
                             session, coo_id, telemetry)
    if not verdict.accepted:
        run.succeeded = False
        run.blocked_reason = f"department_rejected: {verdict.reasoning}"
        return run
    # existing select_agent() + dispatch() unchanged
```

This mirrors the existing `unresolvable_dependency_gap` halt shape exactly (`run.succeeded =
False`, `run.blocked_reason` set, return immediately) - `orchestrator/controller.py`'s
`_receive_multi_department_objective()` already turns any `blocked_reason` into an escalation;
it only needs to recognize the `department_rejected:` prefix and map it to
`EscalationCondition.DEPARTMENT_REJECTED` instead of `UNRESOLVABLE_DEPENDENCY_GAP`.

### 3.6 Adding a new department

Nothing in `COOOrchestrator`, `head.py`, or `execute_workflow()` hardcodes the current five
departments - `DepartmentRegistry.load_all()` and `AgentRegistry.load_all()` both generically
iterate every `departments/*/definition.yaml` and `agents/active/*/agent.yaml` file on disk.
Adding a new department is:

1. Copy an existing `departments/<dept>/definition.yaml` -> edit `id`, `name`, `purpose`,
   `mission`, `capabilities` for the new department's role.
2. Copy an existing `agents/active/<dept>_head/agent.yaml` -> edit the same fields plus
   `mission.objective`/`responsibilities` to reflect what this specific department should and
   shouldn't accept.
3. Copy the worker agent(s) the same way if the new department needs its own specialists.
4. Set the new department's `leader` field to the new head's identity ID.

No code changes are required for the triage mechanism itself. The one thing worth knowing:
`orchestrator/classification.py`'s `_CANONICAL_DEPARTMENT_ORDER` (used only for multi-department
workflow *sequencing*, unrelated to triage) is a fixed list of the current four
dispatch-relevant departments. A new department not in that list still works correctly - it
sorts last via the existing fallback - but if it needs a specific execution position relative
to the others, that one list is the only place to touch.

---

## 4. Error Handling Summary

| Failure | Where | Behavior |
|---|---|---|
| Head call: network/timeout/provider error | `receive_objective()` / `execute_workflow()` | Wrapped the same way classifier failures already are: Decision Record + `TECHNICAL_FAILURE` escalation, then re-raise. |
| Head call: unparseable JSON | Same | Treated as a reject with no valid suggestion (fails toward the conservative outcome - declining is safer than silently proceeding on a verdict we couldn't interpret), same fail-toward-caution spirit as `intake.py`'s sufficiency-check parse failures. |
| Head rejects, 2-attempt cap reached, or no valid suggestion | Single-department path | Decision Record + `DEPARTMENT_REJECTED` escalation, then `DepartmentRejectedError` (treated as a normal completed reply upstream, not an HTTP error). |
| Head rejects mid-workflow | Multi-department path | `run.blocked_reason` set (`department_rejected:` prefix), same `DEPARTMENT_REJECTED` escalation, no rollback of earlier departments' completed work. |
| Suggested department ID: hallucinated, unknown, or already attempted | Both paths | Treated as no valid suggestion, not trusted. |

User-submitted objective text is interpolated directly into the Head's triage prompt, the same
prompt-injection surface Phase 1's classifier and sufficiency check already accepted as a known,
bounded-risk limitation. The bound here is the same shape: a Head's verdict only ever gates
whether dispatch proceeds and where - it grants no elevated access, and a hallucinated/injected
`suggested_department_id` is validated against the real registry regardless of what the model
returns.

---

## 5. Testing Strategy

- **Zero changes needed** for existing tests that construct `COOOrchestrator` without
  specifying a `head` - `AutoAcceptDepartmentHead` preserves today's behavior exactly.
- **New:** `LLMDepartmentHead` - unit tests against a fake `dispatch()`/`AgentRuntime` path (no
  real network calls), covering: accept, reject-with-valid-suggestion,
  reject-with-hallucinated-suggestion (dropped), reject-with-no-suggestion, unparseable
  response (fails toward reject), and a provider/network failure (propagates, does not become
  a verdict).
- **New:** single-department reassignment loop - accept on attempt 1; reject-then-accept on
  attempt 2 at the suggested department; reject-reject exhausts the cap and raises
  `DepartmentRejectedError` with the `DEPARTMENT_REJECTED` escalation written.
- **New:** multi-department workflow - one department's Head rejects mid-sequence; workflow
  halts, earlier `TaskRun`s are present and untouched, `DEPARTMENT_REJECTED` escalation written
  (not `UNRESOLVABLE_DEPENDENCY_GAP`).
- **New, gated:** one real-API smoke test per the pattern every other real-model integration
  already follows (skipped by default).
- **Unchanged:** every existing `receive_objective()`/`execute_workflow()` test path not
  exercising rejection.

---

## 6. Open Items for Future Sub-Projects (explicitly not designed here)

**Deferred, not abandoned**, same as this document's own predecessor. Remaining, in dependency
order:

- Dynamic agent count and specialist agent selection within a department (possibly building on
  `sdk/agent_builder/` from Phase 10).
- Token/cost budget management as a decision input.
- Real model tier selection (Reasoning Tier Classification, RDL sec.8) replacing the current
  fixed default provider/model for actual task execution - the original ask that started this
  whole design process, and the smallest, most downstream piece of it.
