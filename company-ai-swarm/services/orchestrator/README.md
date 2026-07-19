# Orchestrator (COO)

Objective analysis, task decomposition, agent allocation, workflow generation, execution
monitoring.

**Spec:** Specifications/1 - enterprise-architecture/The Company COO Orchestrator Specification (COOS).md

**Status:** Implemented through IMPLEMENTATION_PLAN.md Phase 9 (MVP Version 1.0).
Single-department objectives route via this service's own single-agent dispatch
(Phase 5); objectives matching more than one department - or matching only "operations" (the
Review Agent's department; fixed in Phase 8, see below) - delegate "Create Workflow" to
`services/workflow_engine/` (Phase 6/7). Structural note: CRBS's original scaffolding for
this directory used five empty subdirectories (`planner/`, `allocator/`, `router/`,
`evaluator/`, `controller/`); these were removed and replaced with flat modules of the same
names, for consistency with every other service in this codebase (`identity_service/
models.py`, `security_service/permissions.py`, etc. are all flat, not subdirectory packages).

- `classification.py` - Department Selection (COOS sec.7-9, sec.12), formerly `planner.py`'s
  keyword-overlap matcher, relocated behind a swappable `DepartmentClassifier` Protocol as
  part of the 2026-07-19 dynamic-department-routing work - exactly parallel to
  `shared/model_gateway.py`'s `ModelProvider` pattern. `KeywordDepartmentClassifier` is the
  exact old logic (multi-department support included, via the same fixed canonical
  department sequence rather than a real dependency graph - see its docstring for why, and
  for the discovery that all four MVP departments already have capability-aligned agents
  since Phase 5, not just Research), unchanged and still the dev/test default.
  `LLMDepartmentClassifier` wraps a `ModelGateway` call to classify objectives semantically
  instead of by keyword overlap, selected via `DEPARTMENT_CLASSIFIER=llm`; it validates every
  department ID the model returns against the real registry rather than trusting it.
  `create_classifier_from_env()` picks between them, mirroring
  `shared/providers.create_provider_from_env()`. Complexity scoring remains a fixed default,
  not computed - unrelated to this relocation, and still unchanged since Phase 5/7 (no
  numeric algorithm exists anywhere in the source corpus; the label itself was corrected in
  Phase 7 from "Level 2 Moderate" to "Level 2 Standard" to match TDL sec.7's tier names
  exactly) - now set directly in `controller.py`.
- `intake.py` - COO-level sufficiency check (2026-07-19 design doc), chat-only:
  `assess_sufficiency()` decides whether an objective has enough detail to act on before
  `apps/api_gateway/dashboard_api.py`'s `POST /chat` ever enqueues it (`POST /chat/sync` and
  `POST /objectives` skip it). Round 1 asks one clarifying question if detail is lacking;
  round 2 reframes as an explicit proceed-as-is-or-clarify choice; round 3+ is a hard cap
  enforced in code, with no model call - `sufficient=True` unconditionally, guaranteeing the
  clarification loop terminates. A model-call failure propagates to the caller rather than
  being swallowed as an insufficient verdict; a malformed-but-successful response is caught
  and fails toward insufficient with a generic fallback question instead.
- `allocator.py` - Agent Allocation Engine (COOS sec.13). Capability Match only; Performance
  History, Availability, Cost, and Risk are explicitly not yet implemented (see docstring).
- `router.py` - dispatches to Phase 4's `AgentRuntime` via an `AgentMessageContract`. Reused
  unmodified by `workflow_engine.engine.execute_workflow()` for each department's task. Phase
  9 addition: every successfully-completed task also records a Department-tier OBSERVATION
  memory object, authored by the agent - the mechanism that makes MVS-005's "second execution
  improves via stored knowledge" real (agent_runtime/runtime.py's Retrieve Relevant Knowledge
  step already queried Department-tier memory since Phase 4, but nothing wrote to it before
  now). Best-effort, same reasoning as `_learn()`.
- `evaluator.py` - Outcome Validation Engine (COOS sec.20). "Objective Achieved?" only;
  Quality/Compliance/Risk checks need agents and engines not built until later phases.
- `controller.py` - `COOOrchestrator`, the Operating Cycle (COOS sec.6) end to end.
  `receive_objective()` returns `ObjectiveOutcome` for a single matched substantive
  department (Phase 5 path, unchanged) or `WorkflowObjectiveOutcome` otherwise (Phase 6/7
  path, delegates to `workflow_engine`). Phase 8 fix: a lone match on "operations" now also
  routes through `workflow_engine` rather than the single-agent shortcut, since dispatching
  the raw objective straight to the Review Agent would contradict its own mission - found
  while writing this phase's Gate Integrity Check test. Phase 8 also wires
  `escalation.py`'s four-condition policy into both paths, and wraps dispatch/execute calls
  to catch and log unhandled exceptions as TECHNICAL_FAILURE before re-raising. Phase 9
  implements "Learn" (`_learn()`): tiered lesson promotion (`memory_service/promotion.py`),
  reusing Phase 8's Escalation Records as the sole criticality signal - a workflow with no
  escalation is "minor" (self-approved straight to Historical tier), a workflow with any
  escalation is "critical" (held at Project tier pending human approval). Best-effort, same
  as `router.py`'s Phase 9 addition below: a missing COO memory-write permission is audited,
  never allowed to undo an already-reported objective outcome.
- `decisions.py` / `models.py` - COO Decision Record persistence (COOS sec.22).
  `decisions.py` gained `list_decisions()` in Phase 8 for
  `observability_service/views.py`'s Director/COO views.
- `escalation.py` / `escalations.py` - Phase 8: the four-condition escalation policy
  (ESTAS sec.10 Risk Assessment substitute) and its persistence (`EscalationRecord` in
  `models.py`). See `escalation.py`'s module docstring for the exact four conditions, and
  `technology_decisions.md` for why conditions 2 and 4 aren't reachable through
  `receive_objective()`'s public entry point with this codebase's stub model provider and
  real department files, and are tested as direct exercises of the same functions instead.

**Tests:** `Tests/integration/test_coo_orchestration.py` (Phase 5, single-department),
`Tests/integration/test_workflow_orchestration.py` (Phase 6, multi-department),
`Tests/integration/test_knowledge_graph_review.py` (Phase 7),
`Tests/integration/test_escalation_policy.py` (Phase 8, all four conditions +
technical failure), `Tests/integration/test_lesson_promotion.py` (Phase 9),
`Tests/acceptance/test_mvs_acceptance.py` (Phase 9, full MVS 001-010 suite).
