"""Workflow Engine: multi-department Task Decomposition + Sequential Execution.

Source: Specifications/1 - enterprise-architecture/Enterprise Workflow Orchestration
Specification (EWOS).md sec.10 (Task Decomposition), sec.14 (Sequential Execution),
sec.16 (Department Routing).

Phase 6 scope (IMPLEMENTATION_PLAN.md), and what's deliberately not built yet:

- Decomposition is department-level only: one Task per matched department, not the
  finer-grained multi-task-per-department decomposition sec.10's own example implies
  ("Research requirements -> Architecture design -> Security review -> ..."). Phase 6's test
  is a two-department objective, so this is the smallest decomposition that satisfies it -
  not a claim that finer decomposition isn't needed later.
- Sequencing uses a fixed canonical department order (see orchestrator/classification.py's
  select_all_matching_departments, originally orchestrator/planner.py's), not a real
  dependency graph from EWOS sec.5's `Dependencies` field - no dependency-declaration
  mechanism exists anywhere in this corpus yet (Task Definition Language defines task
  fields, not a graph resolver).
- Parallel Execution (EWOS sec.13) is not implemented - every Phase 6 workflow runs
  sequentially regardless of whether its departments are actually independent.
- If a task's outcome is not achieved, later tasks in the workflow do not run. EWOS sec.14's
  own examples ("Cannot deploy before testing") assume this, and Phase 6 has no
  compensating/rollback logic that would justify continuing past a failed dependency.

Phase 7 addition (MVP Build Order Version 0.3): if the fixed canonical department order
(orchestrator/classification.py, originally orchestrator/planner.py) includes "operations" -
the only MVP department carrying review/evaluation capability, per
agents/active/review_agent/agent.yaml - it is not run as
just another substantive task on the original objective (the Review Agent's own mission
explicitly excludes performing the work it reviews). Instead, once every other matched
department's task has succeeded, a review task is dispatched to it: TDL sec.17's
risk-proportional Task Review, via workflow_engine/review.py's tier mapping. Every completed
task (substantive and review) is also recorded to the Knowledge Graph via
workflow_engine/knowledge.py.

Phase 8 addition (MVP Build Order Version 0.4): if a matched department has no registered
agent (orchestrator/allocator.py's ValueError - a real, not hypothetical, case: a
department.yaml can list an agent ID that was never activated), the workflow does not raise -
it halts gracefully with WorkflowRun.blocked_reason set. This is escalation condition 4
(orchestrator/escalation.py, "unresolvable dependency gap"), a framework verdict the caller
(orchestrator/controller.py) is responsible for turning into an Escalation Record - it is not
treated as a crash. The review step's TDL sec.14 evidence and
workflow_engine/gate_integrity.py's verdict on it (escalation condition 3) are also recorded
onto the WorkflowRun here, for the same reason: this module reports facts, the governance
layer above decides what to do with them.

Department Head Triage addition (Documentation/plans/
2026-07-19-department-head-triage-design.md): each substantive department's Head
(orchestrator/head.py) evaluates the objective immediately before that department's
select_agent()+dispatch() - a reject halts forward progress the same way the missing-agent
case above already does (blocked_reason set, no rollback, no reassignment attempted
mid-workflow), distinguished by a "department_rejected:" prefix instead of
"unresolvable_dependency_gap:" so the caller can classify it correctly. The review step is
not triaged - Section 2 of the design doc scopes triage to substantive departments only.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from observability_service.telemetry import TelemetrySink
from orchestrator.allocator import select_agent
from orchestrator.department_registry import DepartmentDefinition
from orchestrator.evaluator import validate_outcome
from orchestrator.head import AutoAcceptDepartmentHead, DepartmentHead, resolve_verdict_execution
from orchestrator.router import dispatch
from shared.model_gateway import ModelGateway
from workflow_engine.gate_integrity import check_gate_integrity
from workflow_engine.knowledge import record_task_knowledge
from workflow_engine.models import TaskRun, WorkflowRun
from workflow_engine.review import determine_review_tier

REVIEW_DEPARTMENT_ID = "operations"


def execute_workflow(
    session: Session,
    *,
    coo_id: str,
    objective: str,
    required_output: str,
    departments: list[DepartmentDefinition],
    agent_registry: AgentRegistry,
    model_gateway: ModelGateway,
    telemetry: TelemetrySink | None = None,
    complexity_level: str = "Level 2 Standard",
    head: DepartmentHead = AutoAcceptDepartmentHead(),
) -> WorkflowRun:
    run = WorkflowRun(workflow_id=f"WF-{uuid4().hex[:8]}", objective=objective)

    substantive_departments = [d for d in departments if d.id != REVIEW_DEPARTMENT_ID]
    review_department = next((d for d in departments if d.id == REVIEW_DEPARTMENT_ID), None)

    for department in substantive_departments:
        verdict = head.evaluate(
            department,
            objective,
            agent_registry=agent_registry,
            model_gateway=model_gateway,
            session=session,
            coo_id=coo_id,
            telemetry=telemetry,
        )
        if not verdict.accepted:
            run.succeeded = False
            run.blocked_reason = f"department_rejected: {verdict.reasoning}"
            return run

        department_objective = f"{objective} (department: {department.id})"

        # Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): mirrors orchestrator/controller.py's
        # single-department path - if the Head already resolved this department's work itself
        # or spawned a specialist (resolve_verdict_execution()), that result stands and
        # select_agent()+dispatch() is skipped. None reproduces this loop's exact original
        # behavior. A ValueError here means the department has no registered head agent for
        # its `leader` field - the same "can't proceed" shape select_agent()'s ValueError
        # already gets below, not a technical failure.
        try:
            head_execution = resolve_verdict_execution(
                verdict,
                department,
                objective=department_objective,
                required_output=required_output,
                agent_registry=agent_registry,
                model_gateway=model_gateway,
                session=session,
                coo_id=coo_id,
                telemetry=telemetry,
            )
        except ValueError as exc:
            run.succeeded = False
            run.blocked_reason = f"unresolvable_dependency_gap: {exc}"
            return run

        if head_execution is not None:
            execution_result = head_execution
            agent_id = execution_result.artifact.get("agent_id", department.leader)
            knowledge_agent = agent_registry.get(department.leader)
        else:
            try:
                allocation = select_agent(department, agent_registry)
            except ValueError as exc:
                run.succeeded = False
                run.blocked_reason = f"unresolvable_dependency_gap: {exc}"
                return run

            execution_result = dispatch(
                session,
                coo_id=coo_id,
                agent=allocation.agent,
                objective=department_objective,
                required_output=required_output,
                model_gateway=model_gateway,
                telemetry=telemetry,
            )
            agent_id = allocation.agent.identity.id
            knowledge_agent = allocation.agent

        validation = validate_outcome(execution_result)

        run.tasks.append(
            TaskRun(
                task_id=f"TSK-{uuid4().hex[:8]}",
                department=department,
                agent_id=agent_id,
                execution_result=execution_result,
                validation=validation,
            )
        )
        record_task_knowledge(
            session,
            workflow_id=run.workflow_id,
            objective=objective,
            department=department,
            agent=knowledge_agent,
        )

        if not validation.objective_achieved:
            run.succeeded = False
            return run

    if review_department is not None:
        run.review_tier = determine_review_tier(complexity_level)

        try:
            allocation = select_agent(review_department, agent_registry)
        except ValueError as exc:
            run.succeeded = False
            run.blocked_reason = f"unresolvable_dependency_gap: {exc}"
            return run

        reviewed_agents = ", ".join(t.agent_id for t in run.tasks)
        review_task = (
            f"Review tier: {run.review_tier}. Review the outputs produced for objective "
            f"'{objective}' by [{reviewed_agents}] against the required output "
            f"'{required_output}'. Produce a pass/fail validation with documented reasoning."
        )

        execution_result = dispatch(
            session,
            coo_id=coo_id,
            agent=allocation.agent,
            objective=review_task,
            required_output="A pass/fail validation with documented reasoning",
            model_gateway=model_gateway,
            telemetry=telemetry,
        )
        validation = validate_outcome(execution_result)
        review_task_id = f"TSK-{uuid4().hex[:8]}"

        # TDL sec.14 Evidence Model, populated with what's actually available - Confidence
        # Assessment stays None, see gate_integrity.py's docstring for why that's not a gap
        # being papered over.
        evidence = {
            "supporting_artifacts": [t.task_id for t in run.tasks],
            "source_references": [t.agent_id for t in run.tasks],
            "validation_results": {t.agent_id: t.validation.objective_achieved for t in run.tasks},
            "review_records": [review_task_id],
            "confidence_assessment": None,
        }
        run.review_evidence = evidence
        run.gate_superficial = check_gate_integrity(evidence).superficial

        run.tasks.append(
            TaskRun(
                task_id=review_task_id,
                department=review_department,
                agent_id=allocation.agent.identity.id,
                execution_result=execution_result,
                validation=validation,
            )
        )
        record_task_knowledge(
            session,
            workflow_id=run.workflow_id,
            objective=objective,
            department=review_department,
            agent=allocation.agent,
        )

        if not validation.objective_achieved:
            run.succeeded = False
            return run

    run.succeeded = True
    return run
