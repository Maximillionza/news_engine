"""COO Orchestrator: the Operating Cycle (COOS sec.6).

    Receive Objective -> Understand Intent -> Classify Task -> Assess Complexity ->
    Identify Capabilities -> Select Departments -> Select Agents -> Select Models ->
    Create Workflow -> Execute -> Validate -> Learn

Phase 5 scope (IMPLEMENTATION_PLAN.md, MVP Build Order Version 0.1): wired to Research
Department / Research Agent only, via a single already-built AgentRuntime call - "Create
Workflow" was trivial (one task, one agent, no multi-step coordination).

Phase 6 scope (MVP Build Order Version 0.2) adds real multi-department "Create Workflow":
when an objective matches more than one department, receive_objective() delegates to
workflow_engine.execute_workflow() instead of dispatching to a single agent directly. The
single-department path is left exactly as Phase 5 built it (same return type, same Decision
Record shape) so Phase 5's tests keep passing unmodified - Phase 6 is additive, not a
rewrite.

Phase 8 scope (MVP Build Order Version 0.4) wires orchestrator/escalation.py's four-condition
policy into both paths: NO_MATCHING_DEPARTMENT (already-existing rejection path, now also
recorded as an escalation, not just a decision), OUTCOME_NOT_ACHIEVED (either path, when
validation fails), UNRESOLVABLE_DEPENDENCY_GAP (multi-department path, when
workflow_engine.execute_workflow() halts with a blocked_reason), and
GATE_INTEGRITY_SUPERFICIAL (multi-department path, when a review nominally passed but its
evidence didn't). An unhandled exception during dispatch on either path is caught, recorded
as TECHNICAL_FAILURE (distinct from the four framework verdicts), and re-raised - logged, not
swallowed.

Phase 9 scope (MVP Version 1.0) implements "Learn" (see _learn()): tiered lesson promotion,
reusing Phase 8's escalation records as the sole criticality signal rather than a second risk
classification. Best-effort, same as router.py's Phase 9 department-observation write: a
missing memory-write permission is audited, never allowed to undo an already-reported
objective outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from agent_runtime.runtime import ExecutionResult
from memory_service.models import MemoryTier, MemoryType
from memory_service.promotion import request_promotion
from memory_service.repository import write_memory
from observability_service.telemetry import TelemetrySink
from orchestrator import decisions, escalations, intake
from orchestrator.allocator import select_agent
from orchestrator.classification import DepartmentClassifier, KeywordDepartmentClassifier
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.evaluator import OutcomeValidation, validate_outcome
from orchestrator.router import dispatch
from security_service.audit import write_audit_record
from shared.model_gateway import ModelGateway
from workflow_engine.engine import REVIEW_DEPARTMENT_ID, execute_workflow
from workflow_engine.gate_integrity import check_gate_integrity
from workflow_engine.models import WorkflowRun


class NoMatchingDepartmentError(Exception):
    pass


@dataclass
class TaskProfile:
    """Replaces orchestrator/planner.py's TaskProfile (Documentation/plans/
    2026-07-19-dynamic-department-routing-design.md Section 3.3) - same fields except
    match_score is dropped (a keyword-overlap count with no LLM-classification equivalent;
    confirmed unused outside planner.py before removing it)."""

    task_id: str
    objective: str
    complexity_level: str
    matched_department: DepartmentDefinition | None
    reasoning: str


@dataclass
class ObjectiveOutcome:
    """Phase 5 return shape: exactly one department, one agent, one execution."""

    decision_id: str
    task_profile: TaskProfile
    execution_result: ExecutionResult
    validation: OutcomeValidation


@dataclass
class WorkflowObjectiveOutcome:
    """Phase 6 return shape: an objective that matched more than one department, executed as
    a sequential workflow (workflow_engine.execute_workflow())."""

    decision_id: str
    matched_departments: list[DepartmentDefinition]
    workflow: WorkflowRun

    @property
    def objective_achieved(self) -> bool:
        return self.workflow.succeeded


class COOOrchestrator:
    def __init__(
        self,
        *,
        coo_id: str,
        department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        telemetry: TelemetrySink | None = None,
        classifier: DepartmentClassifier = KeywordDepartmentClassifier(),
    ) -> None:
        self.coo_id = coo_id
        self._departments = department_registry
        self._agents = agent_registry
        self._model_gateway = model_gateway
        self._telemetry = telemetry
        self._classifier = classifier

    def assess_sufficiency(
        self, objective: str, recent_messages: list[tuple[str, str]], *, round_number: int
    ) -> intake.SufficiencyAssessment:
        """Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.2 -
        thin delegation to orchestrator/intake.py, keeping ModelGateway access encapsulated
        inside COOOrchestrator (the same discipline this class already applies to
        receive_objective()'s use of self._model_gateway)."""

        return intake.assess_sufficiency(
            self._model_gateway, objective, recent_messages, self._departments, round_number
        )

    def receive_objective(
        self, session: Session, objective: str, *, required_output: str
    ) -> ObjectiveOutcome | WorkflowObjectiveOutcome:
        decision_id = f"DEC-{uuid4().hex[:8]}"

        # Understand Intent -> Classify Task -> Assess Complexity -> Identify Capabilities
        # -> Select Departments. One classification call (Documentation/plans/
        # 2026-07-19-dynamic-department-routing-design.md Section 3.3) replaces what used
        # to be two separate keyword-matching calls (select_all_matching_departments() then,
        # for the single-department path, a second internal match inside analyze_objective())
        # - wasteful even when both were free, and actively costly now that a real classifier
        # may make a network call. Both the multi-department decision and the
        # single-department TaskProfile are derived from this one result.
        #
        # Phase 8 fix (unchanged): a lone match on "operations" (the Review Agent's
        # department) must NOT take the single-agent shortcut - it would dispatch the
        # original objective straight to the Review Agent as if it were primary work,
        # contradicting review_agent/agent.yaml's own mission ("does not perform the
        # original work it reviews"). Routed through the Workflow Engine instead, same as
        # any other multi-department match.
        try:
            classification = self._classifier.classify(objective, self._departments)
        except Exception as exc:
            # Mirrors dispatch()'s and execute_workflow()'s existing failure handling further
            # down this method (and in _receive_multi_department_objective) - a classifier
            # failure must leave the same audit trail (Decision Record + TECHNICAL_FAILURE
            # escalation) any other technical failure does, not silently propagate with
            # nothing written. Found during this plan's self-review: the first draft let this
            # raise before any record existed at all.
            decisions.write_decision(
                session,
                id=decision_id,
                objective=objective,
                reasoning=f"Classification failed: {type(exc).__name__}: {exc}",
                chosen_action="reject: classification failed",
            )
            escalations.write_escalation(
                session,
                condition=EscalationCondition.TECHNICAL_FAILURE,
                reasoning=f"{type(exc).__name__}: {exc}",
                decision_id=decision_id,
                is_technical_failure=True,
            )
            raise

        matched_departments = classification.matched_departments
        routes_through_workflow_engine = len(matched_departments) > 1 or (
            len(matched_departments) == 1 and matched_departments[0].id == REVIEW_DEPARTMENT_ID
        )

        if not matched_departments:
            decisions.write_decision(
                session,
                id=decision_id,
                objective=objective,
                reasoning=classification.reasoning,
                chosen_action="reject: no matching department",
            )
            escalations.write_escalation(
                session,
                condition=EscalationCondition.NO_MATCHING_DEPARTMENT,
                reasoning=classification.reasoning,
                decision_id=decision_id,
            )
            raise NoMatchingDepartmentError(classification.reasoning)

        if routes_through_workflow_engine:
            return self._receive_multi_department_objective(
                session,
                objective,
                required_output=required_output,
                decision_id=decision_id,
                matched_departments=matched_departments,
            )

        task_profile = TaskProfile(
            task_id=f"TSK-{uuid4().hex[:8]}",
            objective=objective,
            # Fixed default - real complexity scoring is deferred (design doc Section 2);
            # unchanged from orchestrator/planner.py's original placeholder.
            complexity_level="Level 2 Standard",
            matched_department=matched_departments[0],
            reasoning=classification.reasoning,
        )

        # Select Agents
        allocation = select_agent(task_profile.matched_department, self._agents)

        # Select Models: delegated entirely to the already-constructed ModelGateway
        # (RDL sec.14 - "Agents SHALL not directly depend on individual models"; the COO
        # doesn't pick a model either, for the same reason).

        decisions.write_decision(
            session,
            id=decision_id,
            objective=objective,
            reasoning=f"{task_profile.reasoning} {allocation.reasoning}",
            chosen_action=f"execute via {allocation.agent.identity.id}",
            options_considered=[d.id for d in self._departments.all()],
            agents_selected=[allocation.agent.identity.id],
            models_used=["stub"],  # Phase 5 has exactly one provider; see model_gateway.py
        )

        # Create Workflow + Execute: Phase 5 has no multi-step workflow to build - dispatch
        # directly to the one selected agent.
        try:
            execution_result = dispatch(
                session,
                coo_id=self.coo_id,
                agent=allocation.agent,
                objective=objective,
                required_output=required_output,
                model_gateway=self._model_gateway,
                telemetry=self._telemetry,
            )
        except Exception as exc:
            escalations.write_escalation(
                session,
                condition=EscalationCondition.TECHNICAL_FAILURE,
                reasoning=f"{type(exc).__name__}: {exc}",
                decision_id=decision_id,
                is_technical_failure=True,
            )
            raise

        # Validate
        validation = validate_outcome(execution_result)

        decisions.update_outcome(
            session,
            decision_id=decision_id,
            outcome=(
                f"objective_achieved={validation.objective_achieved}; "
                f"output_length={len(execution_result.output)}"
            ),
        )

        if not validation.objective_achieved:
            # Note: unreachable through this method's own dispatch() call in practice -
            # AgentRuntime's Validate step (Phase 4) raises before ever returning a result
            # with incomplete steps or empty output, so any ExecutionResult that reaches here
            # already has objective_achieved=True. The branch is kept because it's still
            # correct (validate_outcome() is a real, general function, not written only for
            # this call site) and documented rather than deleted - see
            # Documentation/operations/technology_decisions.md's Phase 8 note.
            escalations.write_escalation(
                session,
                condition=EscalationCondition.OUTCOME_NOT_ACHIEVED,
                reasoning=validation.reasoning,
                decision_id=decision_id,
            )

        self._learn(
            session,
            decision_id=decision_id,
            lesson_content=(
                f"Objective '{objective}' executed via {allocation.agent.identity.id}: "
                f"{validation.reasoning}"
            ),
        )

        return ObjectiveOutcome(
            decision_id=decision_id,
            task_profile=task_profile,
            execution_result=execution_result,
            validation=validation,
        )

    def _receive_multi_department_objective(
        self,
        session: Session,
        objective: str,
        *,
        required_output: str,
        decision_id: str,
        matched_departments: list[DepartmentDefinition],
    ) -> WorkflowObjectiveOutcome:
        """Phase 6 path (IMPLEMENTATION_PLAN.md, MVP Build Order Version 0.2), extended in
        Phase 7 (Version 0.3): Create Workflow + Execute + Validate for an objective spanning
        multiple departments, via workflow_engine.execute_workflow(). Select Agents/Select
        Models happen inside the Workflow Engine, once per department, in the fixed
        canonical order the classifier already resolved (`orchestrator/classification.py`'s
        `_canonical_sort_key`). If "operations"
        (the Review Agent's department) is among the matched departments, the Workflow
        Engine appends TDL sec.17's risk-proportional review step after the others succeed -
        this method doesn't special-case that, it only reports whatever workflow.tasks and
        workflow.review_tier come back with."""

        reasoning = (
            f"Objective matched {len(matched_departments)} departments: "
            f"{[d.id for d in matched_departments]}, in execution order."
        )
        chosen_action = f"execute workflow across {[d.id for d in matched_departments]}"

        try:
            workflow = execute_workflow(
                session,
                coo_id=self.coo_id,
                objective=objective,
                required_output=required_output,
                departments=matched_departments,
                agent_registry=self._agents,
                model_gateway=self._model_gateway,
                telemetry=self._telemetry,
            )
        except Exception as exc:
            # Decision record still needs to exist for the escalation to reference - the
            # normal-path write below (with agents_selected) never ran.
            decisions.write_decision(
                session,
                id=decision_id,
                objective=objective,
                reasoning=reasoning,
                chosen_action=chosen_action,
                options_considered=[d.id for d in self._departments.all()],
            )
            escalations.write_escalation(
                session,
                condition=EscalationCondition.TECHNICAL_FAILURE,
                reasoning=f"{type(exc).__name__}: {exc}",
                decision_id=decision_id,
                is_technical_failure=True,
            )
            raise

        decisions.write_decision(
            session,
            id=decision_id,
            objective=objective,
            reasoning=reasoning,
            chosen_action=chosen_action,
            options_considered=[d.id for d in self._departments.all()],
            agents_selected=[t.agent_id for t in workflow.tasks],
            models_used=["stub"],  # Phase 6 still has exactly one provider; see model_gateway.py
        )

        decisions.update_outcome(
            session,
            decision_id=decision_id,
            outcome=(
                f"objective_achieved={workflow.succeeded}; "
                f"departments={[t.department.id for t in workflow.tasks]}; "
                f"tasks_completed={len(workflow.tasks)}/{len(matched_departments)}; "
                f"review_tier={workflow.review_tier}"
            ),
        )

        if workflow.blocked_reason is not None:
            escalations.write_escalation(
                session,
                condition=EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP,
                reasoning=workflow.blocked_reason,
                decision_id=decision_id,
            )
        elif not workflow.succeeded:
            escalations.write_escalation(
                session,
                condition=EscalationCondition.OUTCOME_NOT_ACHIEVED,
                reasoning=(
                    f"Workflow did not complete: "
                    f"tasks_completed={len(workflow.tasks)}/{len(matched_departments)}"
                ),
                decision_id=decision_id,
            )

        if workflow.gate_superficial and workflow.succeeded:
            missing = check_gate_integrity(workflow.review_evidence or {}).missing_fields
            escalations.write_escalation(
                session,
                condition=EscalationCondition.GATE_INTEGRITY_SUPERFICIAL,
                reasoning=(
                    f"Review for workflow {workflow.workflow_id} nominally passed but its "
                    f"evidence was incomplete: missing {missing}."
                ),
                decision_id=decision_id,
            )

        self._learn(
            session,
            decision_id=decision_id,
            lesson_content=(
                f"Objective '{objective}' executed as a workflow across "
                f"{[t.department.id for t in workflow.tasks]}: "
                f"objective_achieved={workflow.succeeded}."
            ),
        )

        return WorkflowObjectiveOutcome(
            decision_id=decision_id,
            matched_departments=matched_departments,
            workflow=workflow,
        )

    def _learn(self, session: Session, *, decision_id: str, lesson_content: str) -> None:
        """COOS sec.6 Learn step (Phase 9): tiered lesson promotion.

        Criticality reuses Phase 8's escalation policy as the sole signal - a workflow is
        "critical" iff it produced at least one Escalation Record for this decision_id, not
        a second, separately-invented risk classification. Minor lessons are self-approved
        by the COO straight onto the Historical tier; critical lessons are held at
        Project-tier (project_id=decision_id) with an explicit pending LessonPromotion (see
        memory_service/promotion.py) until a human approves or rejects - this call does not
        block on that, it only creates the request."""

        is_critical = bool(escalations.list_escalations_for_decision(session, decision_id))
        lesson_id = f"LESSON-{uuid4().hex[:8]}"

        try:
            if is_critical:
                memory = write_memory(
                    session,
                    identity_id=self.coo_id,
                    id=lesson_id,
                    type=MemoryType.LESSON,
                    content=lesson_content,
                    creator=self.coo_id,
                    tier=MemoryTier.PROJECT,
                    project_id=decision_id,
                )
                request_promotion(
                    session,
                    memory_object_id=memory.id,
                    reason=(
                        f"Workflow for decision {decision_id} tripped an escalation "
                        f"condition - requires human review before Historical-tier "
                        f"promotion."
                    ),
                )
                promotion_note = "promotion=pending_approval"
            else:
                write_memory(
                    session,
                    identity_id=self.coo_id,
                    id=lesson_id,
                    type=MemoryType.LESSON,
                    content=lesson_content,
                    creator=self.coo_id,
                    tier=MemoryTier.HISTORICAL,
                )
                promotion_note = "promotion=auto-approved"
        except PermissionError as exc:
            write_audit_record(
                session,
                actor=self.coo_id,
                action=f"learn:{decision_id}",
                decision="denied",
                reason=str(exc),
            )
            promotion_note = "promotion=skipped (coo lacks memory write permission)"

        existing = decisions.get_decision(session, decision_id)
        current_outcome = existing.outcome if existing is not None else ""
        decisions.update_outcome(
            session, decision_id=decision_id, outcome=f"{current_outcome}; {promotion_note}"
        )
