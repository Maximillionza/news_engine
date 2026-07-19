"""Proves a classifier failure gets the same audit trail as any other technical failure in
COOOrchestrator.receive_objective() - a Decision Record and a TECHNICAL_FAILURE escalation,
before the exception re-raises. Caught during this plan's self-review: the first draft of
the classifier wiring let this propagate with nothing written at all.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from orchestrator.controller import COOOrchestrator
from orchestrator.decisions import list_decisions
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider


class _FailingClassifier:
    def classify(self, objective, registry):
        raise RuntimeError("classifier exploded")


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def test_classifier_failure_writes_decision_and_escalation_then_reraises(session: Session) -> None:
    coo = COOOrchestrator(
        coo_id="coo",
        department_registry=DepartmentRegistry("."),
        agent_registry=AgentRegistry("."),
        model_gateway=ModelGateway(StubModelProvider()),
        classifier=_FailingClassifier(),
    )

    with pytest.raises(RuntimeError, match="classifier exploded"):
        coo.receive_objective(session, "some objective", required_output="anything")

    decisions = list_decisions(session)
    assert len(decisions) == 1
    assert "classifier exploded" in decisions[0].reasoning

    escalations = list_pending_escalations(session)
    assert len(escalations) == 1
    assert escalations[0].condition == EscalationCondition.TECHNICAL_FAILURE
