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
Learn-step infrastructure, not a parallel mechanism. It does NOT automatically mutate
workflow_engine's runtime behaviour for future objectives - closing that loop (an approved
Evolution proposal actually changing what execute_workflow() does next time) is real,
separate follow-up work, named here rather than silently claimed. This mirrors Phase 9's own
precedent exactly: an approved lesson promotion writes a new memory object, it does not
automatically change any agent's behaviour either.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from evolution_service.detection import detect_inefficiencies
from evolution_service.models import ChangeProposal, ImprovementOpportunity, ProposalStatus
from memory_service.models import MemoryObject, MemoryTier, MemoryType
from memory_service.repository import write_memory
from orchestrator.department_registry import DepartmentDefinition
from security_service.permissions import authorize
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
        self, session: Session, proposal_id: str, *, implementer_identity_id: str
    ) -> MemoryObject:
        """The hard-gate enforcement point: raises unless approval_status is already
        APPROVED (EESIS sec.10, ESTAS sec.21) - there is no path from PENDING straight to
        implemented, and this class exposes no function that skips approve_change()."""

        proposal = self._require_proposal(session, proposal_id)
        if proposal.approval_status != ProposalStatus.APPROVED:
            raise EvolutionApprovalError(
                f"Proposal {proposal_id} must be APPROVED before implementation "
                f"(is {proposal.approval_status}) - EESIS sec.10 / ESTAS sec.21."
            )

        opportunity = session.get(ImprovementOpportunity, proposal.opportunity_id)

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
                f"result: approved and implemented\n"
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

    def _require_proposal(self, session: Session, proposal_id: str) -> ChangeProposal:
        proposal = session.get(ChangeProposal, proposal_id)
        if proposal is None:
            raise ValueError(f"Unknown proposal: {proposal_id}")
        return proposal
