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

from agent_runtime.registry import AgentDefinition, AgentMission, AgentRegistry
from agent_runtime.runtime import ExecutionResult
from observability_service.telemetry import TelemetrySink
from orchestrator.department_registry import DepartmentDefinition
from orchestrator.evaluator import EXPECTED_EXECUTION_STEPS
from orchestrator.router import dispatch
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway


@dataclass
class HeadVerdict:
    accepted: bool
    reasoning: str
    suggested_department_id: str | None = None  # only meaningful when accepted=False
    # Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): only meaningful when accepted=True.
    # resolved_output set means the Head executed the objective itself - no further dispatch
    # needed. needs_specialist=True (resolved_output left None) means the Head determined the
    # work genuinely exceeds what it alone can deliver - see resolve_verdict_execution()
    # below for how that spawns a specialist. Neither set (both default) reproduces today's
    # exact behavior: the caller proceeds with its own select_agent()+dispatch() path -
    # AutoAcceptDepartmentHead never sets either, so every existing call site is unaffected.
    resolved_output: str | None = None
    needs_specialist: bool = False


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


def resolve_verdict_execution(
    verdict: HeadVerdict,
    department: DepartmentDefinition,
    *,
    objective: str,
    required_output: str,
    agent_registry: AgentRegistry,
    model_gateway: ModelGateway,
    session: Session,
    coo_id: str,
    telemetry: TelemetrySink | None,
) -> ExecutionResult | None:
    """Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): given an accepted HeadVerdict, produces
    the ExecutionResult for this department's work when the Head resolved it directly or
    determined a specialist is needed. Returns None when neither applies - every verdict
    AutoAcceptDepartmentHead produces, and any accepted verdict that leaves both fields at
    their default - in which case the caller proceeds with its own unchanged
    select_agent()+dispatch() path exactly as before this phase.

    A spawned specialist reuses the Head's own already-authorized identity rather than a new
    one: AgentRuntime's Check Policies step (agent_runtime/runtime.py) authorizes against
    `agent_execution:{agent_id}`, which a genuinely new identity would have no grant for, and
    security_service.permissions.authorize() denies before that grant is even checked if the
    identity itself was never created. Spawning is realized as the Head adopting a
    specialized mission/capability set for one task, not a separately registered entity -
    matches the deliberately lightweight scope decided for this phase (no new
    AgentRegistry entry, no permanent identity)."""

    if verdict.resolved_output is None and not verdict.needs_specialist:
        return None

    head_agent = agent_registry.get(department.leader)
    if head_agent is None:
        raise ValueError(
            f"Department '{department.id}' has no registered head agent for "
            f"leader '{department.leader}'."
        )

    if verdict.resolved_output is not None:
        # steps_completed must match orchestrator/evaluator.py's EXPECTED_EXECUTION_STEPS
        # exactly for validate_outcome() to treat this as achieved - the Head's own dispatch()
        # call already ran the real Agent Execution Cycle to produce resolved_output (Phase 16
        # Increment 3, LLMDepartmentHead), this is a synthesized ExecutionResult reporting
        # that outcome in the shape the rest of the pipeline expects, not a second cycle.
        return ExecutionResult(
            task=objective,
            output=verdict.resolved_output,
            artifact={"agent_id": head_agent.identity.id, "resolved_by": "head"},
            steps_completed=list(EXPECTED_EXECUTION_STEPS),
        )

    specialist = AgentDefinition(
        identity=head_agent.identity,
        mission=AgentMission(
            objective=(
                f"Specialist role adopted by {head_agent.identity.id} for one task, "
                f"because: {verdict.reasoning}"
            )
        ),
        department=head_agent.department,
        capabilities=head_agent.capabilities,
    )
    result = dispatch(
        session,
        coo_id=coo_id,
        agent=specialist,
        objective=objective,
        required_output=required_output,
        model_gateway=model_gateway,
        telemetry=telemetry,
    )
    result.artifact["resolved_by"] = "specialist"
    result.artifact["specialist_reasoning"] = verdict.reasoning
    return result


class LLMDepartmentHead:
    """Production: dispatches to department.leader's registered head agent via the existing
    dispatch() cycle. Stateless - model_gateway is supplied per call like every other
    DepartmentHead.evaluate() implementation, so this needs no constructor.

    Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): the Head is now asked to attempt the
    objective in the same call that judges whether it belongs to this department, not just
    verdict on it - one dispatch() either produces a real result or a structured reason it
    couldn't. The two conditions under which spawning a specialist (needs_specialist) is
    legitimate: the objective genuinely exceeds one agent's capacity regardless of how much
    detail was given. A third possible outcome - the information given is too incomplete to
    judge scope or headcount at all - is deliberately NOT a spawn trigger: another agent
    doesn't have any context the Head lacks, so spawning wouldn't fix an information deficit.
    That case is folded into a rejection (accepted=False) instead, distinguishable in its
    reasoning text, since Phase 15's intake sufficiency check should make it rare - if it
    starts firing often, that's a signal Phase 15's gate has a gap, not that this Head needs
    more agents."""

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
                f"You are the Head of the {department.name} ({department.mission}). "
                f"An objective has been routed to your department: {objective}"
            ),
            required_output=(
                "Decide, and act, in one pass. First: does this objective genuinely belong "
                "to your department, or should it be rejected (wrong department, or not "
                "worth dispatching the swarm for)? If it belongs here: can you complete it "
                "yourself with the information given, does it genuinely exceed what one "
                "agent can deliver regardless of how much detail you have, or is the "
                "information given too incomplete for you to judge either question?\n\n"
                "Respond with ONLY a JSON object in exactly this shape:\n"
                '{"accepted": true|false, "reasoning": "...", '
                '"suggested_department_id": "<id>|null", "resolved": true|false, '
                '"output": "<your actual answer, only if resolved=true>|null", '
                '"needs_specialist": true|false, "insufficient_information": true|false}\n\n'
                "If accepted=false: resolved/output/needs_specialist/"
                "insufficient_information are ignored.\n"
                "If accepted=true and you can complete this yourself: resolved=true, "
                "output=<your actual, complete answer>, needs_specialist=false, "
                "insufficient_information=false.\n"
                "If accepted=true but this genuinely needs more than one agent regardless of "
                "detail given: resolved=false, needs_specialist=true, output=null.\n"
                "If accepted=true but the information given is too incomplete to judge scope "
                "or headcount: resolved=false, insufficient_information=true, output=null."
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

        if not accepted:
            suggested = data.get("suggested_department_id")
            return HeadVerdict(
                accepted=False,
                reasoning=reasoning,
                suggested_department_id=suggested if isinstance(suggested, str) else None,
            )

        if bool(data.get("insufficient_information", False)):
            # Deliberately a rejection, not a spawn trigger - see this class's docstring.
            # No suggested_department_id: this isn't "wrong department," it's "can't judge
            # from what was given," which another department wouldn't resolve either.
            return HeadVerdict(
                accepted=False,
                reasoning=f"Insufficient information to determine scope or headcount: {reasoning}",
                suggested_department_id=None,
            )

        if bool(data.get("resolved", False)):
            output = data.get("output")
            # Coerced to "" rather than left None on a malformed/missing output: resolve_
            # verdict_execution() treats resolved_output=None as "fall through to normal
            # dispatch," which would silently mask the Head claiming resolution without
            # actually producing anything. "" flows through as a real (failed) execution
            # instead - validate_outcome() correctly marks empty output as not achieved,
            # surfacing via the existing OUTCOME_NOT_ACHIEVED escalation path.
            return HeadVerdict(
                accepted=True,
                reasoning=reasoning,
                resolved_output=output if isinstance(output, str) else "",
            )

        return HeadVerdict(
            accepted=True,
            reasoning=reasoning,
            needs_specialist=bool(data.get("needs_specialist", False)),
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
