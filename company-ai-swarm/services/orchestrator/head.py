"""Department Head Triage.

Source: Documentation/plans/2026-07-19-department-head-triage-design.md. Every
departments/*/definition.yaml already carries a `leader` field (DOMS sec.5/8-9) but nothing
in the codebase ever read it or acted on it - once orchestrator/classification.py picked a
department, that department had no say. This module gives each dispatch-relevant department a
real Head agent that can accept or reject an objective before COOOrchestrator.receive_objective()
commits to it, via the same dispatch() (orchestrator/router.py) -> AgentRuntime.execute_task()
cycle any other agent's work already goes through - not a bespoke model_gateway.generate() call
like classification.py/intake.py use, per DOMS sec.8's Leader accountability.

Two swappable implementations of one interface, exactly parallel to
orchestrator/classification.py's DepartmentClassifier pattern:

- AutoAcceptDepartmentHead (dev/test default): always accepts, zero model/dispatch calls,
  mirrors KeywordDepartmentClassifier's zero-network-call nature.
  COOOrchestrator.__init__ defaults to this, so every existing call site that constructs a
  COOOrchestrator without a `head` kwarg needs zero changes.
- LLMDepartmentHead: production, dispatches to the department's own registered head agent.
  Selected via DEPARTMENT_HEAD_TRIAGE=llm, exactly parallel to DEPARTMENT_CLASSIFIER.

A suggested_department_id in a reject verdict is NOT validated here - the caller
(orchestrator/controller.py's single-department retry loop, workflow_engine/engine.py's
multi-department loop) is the one holding the real DepartmentRegistry and the set of
departments already attempted in this call, so registry-membership and already-attempted
validation happen there, the same discipline LLMDepartmentClassifier already applies to
hallucinated department IDs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Mapping, Protocol

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from observability_service.telemetry import TelemetrySink
from orchestrator.department_registry import DepartmentDefinition
from orchestrator.router import dispatch
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway


@dataclass
class HeadVerdict:
    accepted: bool
    reasoning: str
    suggested_department_id: str | None = None  # only meaningful when accepted=False


class DepartmentHead(Protocol):
    def evaluate(
        self,
        department: DepartmentDefinition,
        objective: str,
        *,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        session: Session,
        coo_id: str,
        telemetry: TelemetrySink | None,
    ) -> HeadVerdict: ...


class AutoAcceptDepartmentHead:
    """Dev/test default - always accepts, zero calls."""

    def evaluate(self, department: DepartmentDefinition, objective: str, **_: object) -> HeadVerdict:
        return HeadVerdict(
            accepted=True,
            reasoning="Auto-accept (dev/test default).",
            suggested_department_id=None,
        )


class LLMDepartmentHead:
    """Production: dispatches to department.leader's registered head agent via the existing
    dispatch() cycle. Stateless - model_gateway is supplied per call like every other
    DepartmentHead.evaluate() implementation, so this needs no constructor."""

    def evaluate(
        self,
        department: DepartmentDefinition,
        objective: str,
        *,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        session: Session,
        coo_id: str,
        telemetry: TelemetrySink | None,
    ) -> HeadVerdict:
        head_agent = agent_registry.get(department.leader)
        if head_agent is None:
            raise ValueError(
                f"Department '{department.id}' has no registered head agent for "
                f"leader '{department.leader}'."
            )

        result = dispatch(
            session,
            coo_id=coo_id,
            agent=head_agent,
            objective=(
                f"Evaluate whether this objective belongs to the {department.name} "
                f"({department.mission}): {objective}"
            ),
            required_output=(
                'Respond with ONLY a JSON object: {"accepted": true|false, "reasoning": '
                '"...", "suggested_department_id": "<id>|null"}'
            ),
            model_gateway=model_gateway,
            telemetry=telemetry,
        )

        try:
            data = json.loads(strip_code_fence(result.output))
            accepted = bool(data["accepted"])
            reasoning = str(data["reasoning"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return HeadVerdict(
                accepted=False,
                reasoning=(
                    f"Department Head response was not valid JSON in the expected shape: "
                    f"{result.output!r} ({exc})"
                ),
                suggested_department_id=None,
            )

        suggested = data.get("suggested_department_id")
        return HeadVerdict(
            accepted=accepted,
            reasoning=reasoning,
            suggested_department_id=suggested if isinstance(suggested, str) else None,
        )


_HEADS = ("auto_accept", "llm")


def create_head_from_env(env: Mapping[str, str] | None = None) -> DepartmentHead:
    """DEPARTMENT_HEAD_TRIAGE env var: "auto_accept" (default) or "llm" - exactly parallel to
    DEPARTMENT_CLASSIFIER."""

    source = env if env is not None else os.environ
    selected = source.get("DEPARTMENT_HEAD_TRIAGE", "auto_accept").strip().lower()

    if selected == "auto_accept":
        return AutoAcceptDepartmentHead()
    if selected == "llm":
        return LLMDepartmentHead()

    raise ValueError(f"Unknown DEPARTMENT_HEAD_TRIAGE={selected!r}; expected one of {_HEADS}.")
