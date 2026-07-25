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
from orchestrator.allocator import select_agent
from orchestrator.delegations import write_delegation
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.evaluator import EXPECTED_EXECUTION_STEPS
from orchestrator.router import dispatch
from orchestrator.spawns import write_spawn
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway

# Kept in sync with workflow_engine/engine.py's REVIEW_DEPARTMENT_ID - Operations cannot be
# a delegation target, same reason it cannot be dispatched raw objectives as primary work
# (Phase 8): its own mission excludes performing work it reviews.
_REVIEW_DEPARTMENT_ID = "operations"


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
    # Phase 21 (IMPLEMENTATION_PLAN.md, 2026-07-25): only meaningful when accepted=True,
    # resolved_output is None, and needs_specialist is False - mutually exclusive with
    # needs_specialist by construction (LLMDepartmentHead.evaluate() checks this field first).
    # The department ID whose specific input this Head needs to finish the objective itself -
    # not a full handoff (see suggested_department_id above, which IS a full handoff on
    # reject). See resolve_verdict_execution()'s needs_department_help branch for how this
    # gets resolved and fed back to this Head for a final answer.
    needs_department_help: str | None = None


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
        department_registry: DepartmentRegistry | None = None,
        model: str | None = None,
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
    decision_id: str,
    telemetry: TelemetrySink | None,
    department_registry: DepartmentRegistry | None = None,
    head: "DepartmentHead | None" = None,
    delegation_chain: frozenset[str] = frozenset(),
    model: str | None = None,
) -> ExecutionResult | None:
    """Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): given an accepted HeadVerdict, produces
    the ExecutionResult for this department's work when the Head resolved it directly or
    determined a specialist is needed. Returns None when none of resolved_output/
    needs_specialist/needs_department_help apply - every verdict AutoAcceptDepartmentHead
    produces, and any accepted verdict that leaves all three at their default - in which case
    the caller proceeds with its own unchanged select_agent()+dispatch() path exactly as
    before this phase.

    A spawned specialist reuses the Head's own already-authorized identity rather than a new
    one: AgentRuntime's Check Policies step (agent_runtime/runtime.py) authorizes against
    `agent_execution:{agent_id}`, which a genuinely new identity would have no grant for, and
    security_service.permissions.authorize() denies before that grant is even checked if the
    identity itself was never created. Spawning is realized as the Head adopting a
    specialized mission/capability set for one task, not a separately registered entity -
    matches the deliberately lightweight scope decided for this phase (no new
    AgentRegistry entry, no permanent identity).

    Phase 17 addition: every successful specialist spawn writes a SpecialistSpawnRecord
    (orchestrator/spawns.py), keyed to decision_id, feeding the Evolution Engine's
    promotion-detection heuristic.

    Phase 21 (IMPLEMENTATION_PLAN.md, 2026-07-25) addition: needs_department_help routes to
    _resolve_department_delegation() below. `department_registry` and `head` are required for
    that branch to do anything (needed to look up and evaluate the target department) - both
    default to None so every pre-Phase-21 call site (which can never produce a
    needs_department_help verdict) needs zero changes. `delegation_chain` is the set of
    department IDs already involved in this objective, extended by one entry per hop -
    unbounded in depth (no fixed cap), but self-limiting: a department already in the chain
    can never be re-targeted, so the worst case touches every registered department exactly
    once, never loops."""

    if (
        verdict.resolved_output is None
        and not verdict.needs_specialist
        and not verdict.needs_department_help
    ):
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

    if verdict.needs_department_help:
        return _resolve_department_delegation(
            verdict,
            department,
            head_agent=head_agent,
            objective=objective,
            required_output=required_output,
            agent_registry=agent_registry,
            model_gateway=model_gateway,
            session=session,
            coo_id=coo_id,
            decision_id=decision_id,
            telemetry=telemetry,
            department_registry=department_registry,
            head=head,
            delegation_chain=delegation_chain,
            model=model,
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
        model=model,
    )
    result.artifact["resolved_by"] = "specialist"
    result.artifact["specialist_reasoning"] = verdict.reasoning

    # Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23): a historical record of this spawn,
    # feeding the Evolution Engine's promotion detection heuristic - has this department
    # needed a specialist repeatedly enough to justify a dedicated agent? Written after
    # dispatch() succeeds, not before - a spawn that never actually ran shouldn't count
    # toward the pattern.
    write_spawn(
        session,
        decision_id=decision_id,
        department_id=department.id,
        head_agent_id=head_agent.identity.id,
        reasoning=verdict.reasoning,
    )

    return result


def _resolve_department_delegation(
    verdict: HeadVerdict,
    department: DepartmentDefinition,
    *,
    head_agent: AgentDefinition,
    objective: str,
    required_output: str,
    agent_registry: AgentRegistry,
    model_gateway: ModelGateway,
    session: Session,
    coo_id: str,
    decision_id: str,
    telemetry: TelemetrySink | None,
    department_registry: DepartmentRegistry | None,
    head: "DepartmentHead | None",
    delegation_chain: frozenset[str],
    model: str | None = None,
) -> ExecutionResult:
    """Phase 21 (IMPLEMENTATION_PLAN.md, 2026-07-25): resolves a needs_department_help
    verdict - department.id asked target_id for specific help, not a full handoff. Three
    outcomes:

    1. The target is invalid (unknown, no agent, the Review department, or already in
       delegation_chain - i.e. would create a cycle) or department_registry/head weren't
       supplied (pre-Phase-21 call site): the requesting Head is re-dispatched with a note
       explaining the request couldn't be honored, and finishes on its own. This never raises
       - an unhonorable delegation request degrades to "do your best," the same way
       insufficient_information degrades to a rejection rather than a crash.
    2. The target is valid: its own Head is evaluated (recursively, via resolve_verdict_
       execution() with delegation_chain extended by department.id) - the target may resolve
       directly, spawn its own specialist, or itself delegate further (no depth cap, see
       resolve_verdict_execution()'s docstring for why the chain-membership check alone
       bounds this). Whatever it produces is fed back to the ORIGINAL requesting Head in a
       second dispatch() call, asking it to produce a final answer using that input - this is
       the "incorporate the answer" step, not just relaying the sub-department's raw output.
    3. Every successful delegation (outcome 2) writes a DepartmentDelegationRecord
       (orchestrator/delegations.py), decision_id-scoped, mirroring Phase 17's spawn ledger.
    """

    target_id = verdict.needs_department_help
    chain = delegation_chain | {department.id}

    target = department_registry.get(target_id) if department_registry else None
    delegation_valid = (
        department_registry is not None
        and head is not None
        and target is not None
        and bool(target.agents)
        and target.id != _REVIEW_DEPARTMENT_ID
        and target.id not in chain
    )

    if not delegation_valid:
        reason = (
            f"could not be honored (unknown department, no agent assigned, is the Review "
            f"department, or would create a delegation cycle: already-involved departments "
            f"are {sorted(chain)})"
        )
        fallback_objective = (
            f"{objective}\n\nNote: you indicated you needed help from department "
            f"'{target_id}', but that request {reason}. Complete this yourself with what "
            f"you have, and note the limitation in your answer."
        )
        result = dispatch(
            session,
            coo_id=coo_id,
            agent=head_agent,
            objective=fallback_objective,
            required_output=required_output,
            model_gateway=model_gateway,
            telemetry=telemetry,
            model=model,
        )
        result.artifact["resolved_by"] = "head_after_unhonored_delegation"
        result.artifact["requested_department"] = target_id
        return result

    assert target is not None and department_registry is not None and head is not None

    sub_objective = f"Assist the {department.name} with the following: {objective}"
    target_verdict = head.evaluate(
        target,
        sub_objective,
        agent_registry=agent_registry,
        model_gateway=model_gateway,
        session=session,
        coo_id=coo_id,
        telemetry=telemetry,
        department_registry=department_registry,
        model=model,
    )

    if not target_verdict.accepted:
        sub_result_text = f"[{target.name} could not assist: {target_verdict.reasoning}]"
    else:
        sub_execution = resolve_verdict_execution(
            target_verdict,
            target,
            objective=sub_objective,
            required_output="Provide the specific information or artifact requested, concisely.",
            agent_registry=agent_registry,
            model_gateway=model_gateway,
            session=session,
            coo_id=coo_id,
            decision_id=decision_id,
            telemetry=telemetry,
            department_registry=department_registry,
            head=head,
            delegation_chain=chain,
            model=model,
        )
        if sub_execution is None:
            # target Head accepted but neither resolved/specialist/delegated further (e.g.
            # AutoAcceptDepartmentHead in dev/test) - fall through to a normal dispatch, same
            # as every pre-Phase-21 call site does when resolve_verdict_execution() returns
            # None.
            allocation = select_agent(target, agent_registry)
            sub_execution = dispatch(
                session,
                coo_id=coo_id,
                agent=allocation.agent,
                objective=sub_objective,
                required_output="Provide the specific information or artifact requested, concisely.",
                model_gateway=model_gateway,
                telemetry=telemetry,
                model=model,
            )
        sub_result_text = sub_execution.output

    write_delegation(
        session,
        decision_id=decision_id,
        requesting_department_id=department.id,
        target_department_id=target.id,
        reasoning=verdict.reasoning,
        chain_depth=len(chain),
    )

    final_objective = (
        f"{objective}\n\nYou requested help from {target.name}, which responded: "
        f"{sub_result_text}\n\nUsing this, produce your final, complete answer to the "
        f"original objective."
    )
    result = dispatch(
        session,
        coo_id=coo_id,
        agent=head_agent,
        objective=final_objective,
        required_output=required_output,
        model_gateway=model_gateway,
        telemetry=telemetry,
        model=model,
    )
    result.artifact["resolved_by"] = "head_after_delegation"
    result.artifact["delegated_to"] = target.id
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
    more agents.

    Phase 21 (IMPLEMENTATION_PLAN.md, 2026-07-25) addition: a fourth outcome,
    needs_department_help - the objective belongs here and the Head can do most of it, but
    one part genuinely requires another department's specialty (not full ownership - see
    needs_specialist above for "I need more of my own kind of agent," and
    suggested_department_id on reject for "this isn't my department at all"). The prompt
    explicitly instructs the Head to prefer resolving light, in-domain lookups itself and
    only name another department for work that is genuinely that department's specialty -
    this is the founder's original "implicit boundary" (an Engineering agent may do light
    research itself; deep research belongs to Research) made explicit in the instruction
    rather than left for the model to infer unprompted."""

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
        department_registry: DepartmentRegistry | None = None,
        model: str | None = None,
    ) -> HeadVerdict:
        head_agent = agent_registry.get(department.leader)
        if head_agent is None:
            raise ValueError(
                f"Department '{department.id}' has no registered head agent for "
                f"leader '{department.leader}'."
            )

        other_departments = (
            [
                d
                for d in department_registry.all()
                if d.id != department.id and d.agents and d.id != _REVIEW_DEPARTMENT_ID
            ]
            if department_registry is not None
            else []
        )
        other_departments_text = (
            "\n".join(f"- {d.id}: {d.name}. {d.purpose}" for d in other_departments)
            if other_departments
            else "(none known - do not set needs_department_help)"
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
                "agent can deliver regardless of how much detail you have, does it need one "
                "specific piece of help from another department's specialty, or is the "
                "information given too incomplete for you to judge any of this?\n\n"
                f"Other departments (for needs_department_help only - do not use for "
                f"unrelated purposes):\n{other_departments_text}\n\n"
                "Respond with ONLY a JSON object in exactly this shape:\n"
                '{"accepted": true|false, "reasoning": "...", '
                '"suggested_department_id": "<id>|null", "resolved": true|false, '
                '"output": "<your actual answer, only if resolved=true>|null", '
                '"needs_specialist": true|false, "needs_department_help": "<department_id>|null", '
                '"insufficient_information": true|false}\n\n'
                "If accepted=false: resolved/output/needs_specialist/needs_department_help/"
                "insufficient_information are ignored.\n"
                "If accepted=true and you can complete this yourself: resolved=true, "
                "output=<your actual, complete answer>, needs_specialist=false, "
                "needs_department_help=null, insufficient_information=false. Prefer this for "
                "any work within your own domain, including light research or lookups - do "
                "not delegate work you can reasonably do yourself.\n"
                "If accepted=true but you need one specific piece of input that is genuinely "
                "another department's specialty (not full ownership of this objective): "
                "resolved=false, needs_department_help=\"<department_id from the list above>\", "
                "needs_specialist=false, output=null.\n"
                "If accepted=true but this genuinely needs more of your own kind of agent "
                "regardless of detail given: resolved=false, needs_specialist=true, "
                "needs_department_help=null, output=null.\n"
                "If accepted=true but the information given is too incomplete to judge scope "
                "or headcount: resolved=false, insufficient_information=true, output=null."
            ),
            model_gateway=model_gateway,
            telemetry=telemetry,
            model=model,
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

        # Checked before needs_specialist: if a sloppy model response sets both, delegation
        # to another department's specialty takes priority over spawning more of this
        # department's own kind - see HeadVerdict.needs_department_help's docstring for why
        # these are meant to be mutually exclusive. Self-reference (naming its own department)
        # is treated as if unset, since that isn't delegation at all.
        needs_department_help = data.get("needs_department_help")
        if (
            isinstance(needs_department_help, str)
            and needs_department_help.strip()
            and needs_department_help.strip() != department.id
        ):
            return HeadVerdict(
                accepted=True,
                reasoning=reasoning,
                needs_department_help=needs_department_help.strip(),
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
