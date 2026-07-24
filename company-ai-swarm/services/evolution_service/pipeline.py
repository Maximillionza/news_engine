"""Evolution Engine: the improvement-proposal pipeline.

Source: Specifications/1 - enterprise-architecture/Enterprise Evolution & Self-Improvement
Specification (EESIS).md sec.11 (COO Evolution Role: Analyse workflow -> Request simulation
-> Propose improvement -> Implement approved change), sec.13 (Evolution Testing: Proposed
Change -> Simulation -> Testing -> Risk Assessment -> Approval), sec.10 ("Agents SHALL NOT
independently... Modify governance rules"), and ESTAS sec.21 (autonomous action limits: a
change to organizational process requires human approval, never self-granted).

Hard gate, structurally enforced, not just documented: `detect_and_propose()` always creates
a ChangeProposal with approval_status=PENDING - nothing in this module can set it to
APPROVED directly. `approve_change()`/`reject_change()` are the only functions that
transition it, and both require an `approver_identity_id` that must pass
security_service.authorize() against the `evolution:change_proposal` resource - the Evolution
Engine's own identity (`engine_identity_id`, default "evolution_engine") is never granted
this permission by anything in this codebase, so it structurally cannot approve its own
proposals (see Tests/integration/test_evolution_engine.py's test of exactly that).
`implement_change()` raises unless approval_status is already APPROVED - there is no path
from PENDING straight to implemented.

"Implementation" means what EESIS sec.14 (Evolution Memory) and sec.17 (Evolution Feedback
Loop's "Improve" step) describe: the approved change is recorded as adopted organizational
knowledge, via memory_service.write_memory() at the Historical tier - reusing Phase 9's
Learn-step infrastructure, not a parallel mechanism. For every proposal type before Phase 17,
this was ALL implement_change() did - it did NOT automatically mutate workflow_engine's
runtime behaviour for future objectives, and still doesn't for the review-skip proposal
specifically (closing that particular loop remains real, separate, unstarted follow-up work).

Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23) adds the first proposal type where
implement_change() does real work beyond the memory record: action_type="create_agent" calls
sdk.agent_builder.build_agent() on approval - schema-validates, creates identity, grants
permissions, runs a real smoke-test execution, registers into the live AgentRegistry. This
still can't happen without a prior human approve_change() call (the hard gate above is
unchanged), it's just that "implemented" now sometimes means an actual registry change, not
only a memory record describing one.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from evolution_service.detection import detect_inefficiencies, detect_specialist_pattern
from evolution_service.models import ChangeProposal, ImprovementOpportunity, ProposalStatus
from memory_service.models import MemoryObject, MemoryTier, MemoryType
from memory_service.repository import write_memory
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.spawns import list_spawns_for_department
from sdk.agent_builder.builder import AgentDraft, build_agent
from security_service.permissions import authorize
from shared.model_gateway import ModelGateway
from simulation_service.workflow_simulation import simulate_workflow_change


class EvolutionApprovalError(Exception):
    pass


class EvolutionEngine:
    def __init__(self, *, engine_identity_id: str = "evolution_engine") -> None:
        self.engine_identity_id = engine_identity_id

    def detect_and_propose(
        self,
        session: Session,
        *,
        decision_id: str,
        objective: str,
        required_output: str,
        baseline_departments: list[DepartmentDefinition],
        proposed_departments: list[DepartmentDefinition],
        agent_registry,
    ) -> ChangeProposal | None:
        """EESIS sec.11: Analyse workflow -> Request simulation -> Propose improvement.
        Returns None if detect_inefficiencies() found nothing - the engine does not
        fabricate an opportunity to have something to propose."""

        opportunities = detect_inefficiencies(session, decision_id=decision_id)
        if not opportunities:
            return None
        opportunity = opportunities[0]

        simulation = simulate_workflow_change(
            session,
            objective=objective,
            required_output=required_output,
            baseline_departments=baseline_departments,
            proposed_departments=proposed_departments,
            agent_registry=agent_registry,
            scenario=f"Skip empty review for decision {decision_id}",
        )

        proposal = ChangeProposal(
            id=f"PROP-{uuid4().hex[:8]}",
            opportunity_id=opportunity.id,
            target="workflow_engine.execute_workflow: review-with-nothing-to-review",
            current_state=(
                "Review always runs when the review department is matched, even with zero "
                "substantive tasks to review."
            ),
            proposed_state=opportunity.recommended_change,
            reason=opportunity.problem,
            dependencies=[],
            risk=opportunity.risk,
            simulation_run_id=simulation.id,
            approval_status=ProposalStatus.PENDING,
        )
        session.add(proposal)
        session.commit()
        session.refresh(proposal)
        return proposal

    def propose_specialist_agent(
        self,
        session: Session,
        *,
        department: DepartmentDefinition,
        agent_registry: AgentRegistry,
        threshold: int = 3,
    ) -> ChangeProposal | None:
        """Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23): EESIS sec.11 applied to the
        specialist spawn ledger (orchestrator/spawns.py) instead of Phase 8's escalation
        records. Returns None if detect_specialist_pattern() found nothing (fewer than
        `threshold` spawns for this department) - same "does not fabricate an opportunity"
        discipline as detect_and_propose().

        No simulation step, unlike detect_and_propose()'s workflow-skip proposal:
        simulate_workflow_change() compares two department lists through the same workflow,
        which has no meaningful equivalent for "would a dedicated agent do better than
        repeated ad hoc spawning" - there's nothing to dry-run. simulation_run_id is left
        None, which the schema already allows.

        Idempotent: returns None if a create_agent proposal for this department already
        exists and hasn't been rejected - repeated calls (nothing calls this automatically
        yet, same as detect_and_propose() itself isn't called anywhere in production) must
        not spam proposals for a pattern already raised."""

        existing = (
            session.query(ChangeProposal)
            .filter(ChangeProposal.action_type == "create_agent")
            .filter(ChangeProposal.approval_status != ProposalStatus.REJECTED)
            .all()
        )
        for proposal in existing:
            if proposal.action_payload.get("department") == department.id:
                return None

        opportunity = detect_specialist_pattern(
            session, department_id=department.id, threshold=threshold
        )
        if opportunity is None:
            return None

        head_agent = agent_registry.get(department.leader)
        if head_agent is None:
            raise ValueError(
                f"Department '{department.id}' has no registered head agent for "
                f"leader '{department.leader}'."
            )

        spawns = list_spawns_for_department(session, department.id)
        # sorted(): a stable, human-readable payload - dict/set iteration order isn't
        # something to depend on for what a human reviewer sees before approving.
        reasonings = sorted({s.reasoning for s in spawns})

        action_payload = {
            "department": department.id,
            "identity_id": f"{department.id}_specialist_{uuid4().hex[:6]}",
            "name": f"{department.name} Specialist",
            "mission": (
                f"Specializes in the recurring {department.name} need the department head "
                f"has repeatedly spawned a specialist for: {'; '.join(reasonings)}"
            ),
            "capabilities": list(head_agent.capabilities),
        }

        proposal = ChangeProposal(
            id=f"PROP-{uuid4().hex[:8]}",
            opportunity_id=opportunity.id,
            target=f"agent_registry: new dedicated agent for {department.id}",
            current_state=(
                f"Objectives needing this specialization are handled by ad hoc "
                f"Head-spawned specialists ({len(spawns)} times so far)."
            ),
            proposed_state=opportunity.recommended_change,
            reason=opportunity.problem,
            dependencies=[],
            risk=opportunity.risk,
            simulation_run_id=None,
            approval_status=ProposalStatus.PENDING,
            action_type="create_agent",
            action_payload=action_payload,
        )
        session.add(proposal)
        session.commit()
        session.refresh(proposal)
        return proposal

    def approve_change(
        self, session: Session, proposal_id: str, *, approver_identity_id: str, note: str | None = None
    ) -> ChangeProposal:
        auth = authorize(
            session, identity_id=approver_identity_id, resource="evolution:change_proposal", action="approve"
        )
        if not auth.allowed:
            raise EvolutionApprovalError(
                f"{approver_identity_id} may not approve change proposals: {auth.reason}"
            )

        proposal = self._require_proposal(session, proposal_id)
        if proposal.approval_status != ProposalStatus.PENDING:
            raise EvolutionApprovalError(
                f"Proposal {proposal_id} is not PENDING (is {proposal.approval_status})."
            )

        proposal.approval_status = ProposalStatus.APPROVED
        proposal.resolved_by = approver_identity_id
        session.commit()
        session.refresh(proposal)
        return proposal

    def reject_change(
        self, session: Session, proposal_id: str, *, approver_identity_id: str, note: str | None = None
    ) -> ChangeProposal:
        auth = authorize(
            session, identity_id=approver_identity_id, resource="evolution:change_proposal", action="approve"
        )
        if not auth.allowed:
            raise EvolutionApprovalError(
                f"{approver_identity_id} may not reject change proposals: {auth.reason}"
            )

        proposal = self._require_proposal(session, proposal_id)
        if proposal.approval_status != ProposalStatus.PENDING:
            raise EvolutionApprovalError(
                f"Proposal {proposal_id} is not PENDING (is {proposal.approval_status})."
            )

        proposal.approval_status = ProposalStatus.REJECTED
        proposal.resolved_by = approver_identity_id
        session.commit()
        session.refresh(proposal)
        return proposal

    def implement_change(
        self,
        session: Session,
        proposal_id: str,
        *,
        implementer_identity_id: str,
        department_registry: DepartmentRegistry | None = None,
        agent_registry: AgentRegistry | None = None,
        model_gateway: ModelGateway | None = None,
        agents_root: Path | None = None,
    ) -> MemoryObject:
        """The hard-gate enforcement point: raises unless approval_status is already
        APPROVED (EESIS sec.10, ESTAS sec.21) - there is no path from PENDING straight to
        implemented, and this class exposes no function that skips approve_change().

        The four new keyword-only parameters (Phase 17, IMPLEMENTATION_PLAN.md, 2026-07-23)
        are only required when proposal.action_type == "create_agent" - every proposal type
        that existed before this phase (action_type defaults to "record_only") ignores them
        entirely, so every pre-Phase-17 call site is unaffected."""

        proposal = self._require_proposal(session, proposal_id)
        if proposal.approval_status != ProposalStatus.APPROVED:
            raise EvolutionApprovalError(
                f"Proposal {proposal_id} must be APPROVED before implementation "
                f"(is {proposal.approval_status}) - EESIS sec.10 / ESTAS sec.21."
            )

        opportunity = session.get(ImprovementOpportunity, proposal.opportunity_id)

        if proposal.action_type == "create_agent":
            self._implement_create_agent(
                session,
                proposal,
                department_registry=department_registry,
                agent_registry=agent_registry,
                model_gateway=model_gateway,
                agents_root=agents_root,
            )
            result_line = "result: approved, implemented, and registered as a new agent"
        else:
            result_line = "result: approved and implemented"

        # EESIS sec.14 Evolution Memory schema, written as a Historical-tier lesson -
        # reuses Phase 9's memory_service.write_memory(), not a parallel mechanism.
        memory = write_memory(
            session,
            identity_id=implementer_identity_id,
            id=f"EVOMEM-{uuid4().hex[:8]}",
            type=MemoryType.LESSON,
            content=(
                f"change: {proposal.proposed_state}\n"
                f"reason: {proposal.reason}\n"
                f"{result_line}\n"
                f"benefit: {opportunity.expected_benefit if opportunity else ''}\n"
                f"failure: none\n"
                f"lesson: {proposal.target} - approved via human review, not self-granted."
            ),
            creator=implementer_identity_id,
            tier=MemoryTier.HISTORICAL,
        )

        proposal.approval_status = ProposalStatus.IMPLEMENTED
        session.commit()
        session.refresh(proposal)
        return memory

    def _implement_create_agent(
        self,
        session: Session,
        proposal: ChangeProposal,
        *,
        department_registry: DepartmentRegistry | None,
        agent_registry: AgentRegistry | None,
        model_gateway: ModelGateway | None,
        agents_root: Path | None,
    ) -> None:
        """The first case of implement_change() doing real work beyond a memory record - see
        this module's docstring. Builds the same sdk.agent_builder.AgentDraft
        propose_specialist_agent() derived the proposal from, out of action_payload, and runs
        it through the unmodified build_agent() pipeline: schema validation, identity
        creation, permission grants, a real smoke-test execution, live AgentRegistry
        registration."""

        missing = [
            name
            for name, value in (
                ("department_registry", department_registry),
                ("agent_registry", agent_registry),
                ("model_gateway", model_gateway),
                ("agents_root", agents_root),
            )
            if value is None
        ]
        if missing:
            raise EvolutionApprovalError(
                f"Proposal {proposal.id} is action_type=create_agent, which requires "
                f"{', '.join(missing)} to implement - none were supplied."
            )

        payload = proposal.action_payload
        draft = AgentDraft(
            identity_id=payload["identity_id"],
            name=payload["name"],
            department=payload["department"],
            mission=payload["mission"],
            capabilities=list(payload.get("capabilities", [])),
        )
        build_agent(
            draft,
            session=session,
            department_registry=department_registry,
            agent_registry=agent_registry,
            model_gateway=model_gateway,
            agents_root=agents_root,
        )

    def _require_proposal(self, session: Session, proposal_id: str) -> ChangeProposal:
        proposal = session.get(ChangeProposal, proposal_id)
        if proposal is None:
            raise ValueError(f"Unknown proposal: {proposal_id}")
        return proposal
