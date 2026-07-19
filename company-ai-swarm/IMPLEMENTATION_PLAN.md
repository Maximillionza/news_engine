# The Company — Milestone-Based Implementation Plan

Version 1.0. No code has been written against this plan — it is a planning artifact only,
synthesizing the build sequences already defined across `Specifications/2 -
construction-framework/Enterprise Implementation Blueprint (EIB).md`, `Specifications/3 -
execution-framework/AI Builder Master Execution Package (ABMEP).md`, and `Specifications/3 -
execution-framework/MVP Validation Specification (MVS).md` into one concrete, testable
sequence.

## How to read this document

Twelve phases. Each phase has:

- **Depends on** — which prior phases must be *done* (not just started) before this one can begin.
- **Deliverables** — what gets built, named against the repository structure already scaffolded (`agents/`, `services/`, `departments/`, etc.).
- **Test** — how this phase is validated **on its own**, without needing any later phase to exist. This is the hard requirement: if a phase's test can only pass once a future phase is also built, the phase boundary is wrong and should be redrawn.
- **Exit criteria** — the observable state that means "this phase is done."

Phases 0–9 constitute the MVS-canonical MVP (Director + COO + Research/Engineering/
Compliance/Operations departments + one agent each + full governance layer). Phases 10–11
are explicitly post-MVP, per EIB Phase 3/4 and CCBP §10 ("First Expansion After MVP").


## Phase dependency graph

```
Phase 0  Foundation & Contracts
   │
Phase 1  Identity & Security Core
   │
Phase 2  Data Layer & Memory Substrate
   │
Phase 3  Runtime & Communication Backbone
   │
Phase 4  Agent Runtime (single agent, no orchestration)
   │
Phase 5  COO + single department (Research)          ── MVP v0.1
   │
Phase 6  Multi-department (+ Engineering, Compliance) ── MVP v0.2
   │
Phase 7  Knowledge Graph + full 4-dept roster         ── MVP v0.3
   │
Phase 8  Governance completion                        ── MVP v0.4
   │
Phase 9  MVP validation (MVS 001–010)                 ── MVP v1.0
   │
   ├── Phase 10  Expansion layer (SDK/Plugin/Marketplace/API)
   │
   └── Phase 11  Intelligence systems (Digital Twin/Simulation/Evolution)
```

No phase may begin before its predecessor's exit criteria are met. This mirrors the Build
Dependencies chain in EIB §12 (Identity → Security → Runtime → Agents → Workflows →
Departments → Expansion Systems).


---

## Phase 0 — Foundation & Contracts

**Depends on**: nothing (repository structure and configuration templates already exist —
see `CRBS`, `agents/templates/agent_template.yaml`, `Configuration/company.yaml`).

**Deliverables**:

- Development environment (Python, FastAPI, PostgreSQL, per `EIAS` §4-8 and `CCBP` §6) — buildable and runnable, no application logic yet.
- `RCS`'s Universal Request Contract, Universal Response Contract, Event Contract, and Service Contract implemented as validated schemas (JSON Schema / Pydantic models), per RCS Principle 004 "contracts before implementation."
- `documentation/technology_decisions.md` recording the concrete stack choices.

**Test**: A schema-validation test suite loads each contract schema and validates a hand-written example payload against it (one valid, one deliberately invalid per contract type, expecting rejection). The dev environment builds and serves a placeholder health-check endpoint.

**Exit criteria**: All four RCS contract schemas exist, are validated by an automated test, and no application code depends on anything beyond these schemas and the running dev environment.


## Phase 1 — Identity & Security Core

**Depends on**: Phase 0 (contracts exist to shape identity/security_context payloads).

**Deliverables**:

- Identity service: create/read identity records for humans, agents, services (`ESTAS` §5-7).
- Permission model: role + resource + action + scope evaluation (`ESTAS` §8-9, `ECLS` §11).
- Audit log sink: every identity/permission action produces an audit record (`ESTAS` §24).

**Test**: MVS Test Category 007 (Security Validation), run in isolation against the identity/permission service alone — no agents exist yet:

1. Attempt an action with no identity → denied, logged.
2. Attempt an action with insufficient permission → denied, logged.
3. Attempt an action with correct permission → allowed, logged.

**Exit criteria**: All three security test cases pass, and every attempt (allowed or denied) has a corresponding audit record with actor, action, timestamp, and decision.


## Phase 2 — Data Layer & Memory Substrate

**Depends on**: Phase 1 (memory access requires identity/permission checks per `ESTAS` §16).

**Deliverables**:

- Operational database, vector store, graph store, object storage provisioned (`EIAS` §8).
- Memory service implementing the canonical five-tier hierarchy — Working, Project, Department, Enterprise, Historical (`EMAS` §5, `memory/schemas/memory_object_template.yaml`).
- Knowledge object storage (entities/relationships tables), not yet wired to any graph query engine.

**Test**: Memory CRUD test suite, run without any agent runtime:

1. Write a memory object to each of the five tiers.
2. Retrieve it and confirm all EMAS-required fields persisted (context, confidence, validation_status, applicability, expiration).
3. Confirm tier isolation: a Project-tier memory written under Project A is not returned when querying Project B's context (`EMAS` §13 Context Filtering).

**Exit criteria**: All five tiers support write/read, and the isolation test demonstrates no cross-project leakage.


## Phase 3 — Runtime & Communication Backbone

**Depends on**: Phase 0 (contracts), Phase 1 (security_context is mandatory on every message per `RCS` §6).

**Deliverables**:

- Service framework hosting the API Gateway (`services/orchestrator` scaffolding already exists).
- Event Bus and Service Bus implementations (`services/event_service`, per `EEBS`/`ESBS` design in Tier 4 — implemented now since core communication is MVP-critical, unlike the SDK/Plugin/Marketplace layer those documents also describe).
- Structured logging and telemetry emission (`EOCCS` §6 Enterprise Telemetry Model).

**Test**: Synthetic producer/consumer test, no real agents:

1. A test service registers on the Service Bus and responds to a request using the RCS Universal Request/Response Contract.
2. A test event is published on the Event Bus and received by a subscribed test consumer.
3. Both actions appear in telemetry with correct component/action/timestamp/duration fields.

**Exit criteria**: Synthetic request-response and publish-subscribe both succeed, both produce telemetry, and both carry a valid security_context validated in Phase 1.


## Phase 4 — Agent Runtime (single agent, no orchestration)

**Depends on**: Phase 2 (memory access), Phase 3 (communication, telemetry).

**Deliverables**:

- Agent Runtime engine implementing the Agent Execution Cycle: Receive Task → Load Context → Retrieve Knowledge → Check Policies → Plan → Execute → Validate → Produce Artifact → Report Outcome → Release Context (`ROM` §11).
- Agent Registry (`agents/active/`, already scaffolded with `research_agent`, `engineering_agent`, `compliance_agent`, `review_agent` templates).
- Model Gateway routing stub — may route to a single model provider initially; the abstraction (`Agent → Model Gateway → Selected Model`, per `RDL` §11 / `EIAS` §11) must exist even if the routing logic is trivial.

**Test**: Load `research_agent/agent.yaml`, issue one canned task directly to the Agent Runtime (bypassing the COO entirely), and confirm:

1. The agent runtime traverses all nine Agent Execution Cycle steps (observable via telemetry from Phase 3).
2. Output is produced and an audit record exists (Phase 1).
3. The agent never calls a model directly — only through the Model Gateway.

**Exit criteria**: One agent runs a task end-to-end without a COO in the loop, and the model-abstraction rule is verifiably enforced (test fails if the agent's code path bypasses the gateway).


## Phase 5 — COO + Single Department — MVP Version 0.1

**Depends on**: Phase 4.

**Deliverables**:

- COO Orchestrator's Task Analysis, Agent Allocation, and Model Routing engines (`COOS` §7-14), wired only to the Research Department / Research Agent.
- Basic task router.
- COO Decision Record persistence (`COOS` §22).

**Test**: MVS Test Category 001 (Objective Execution), constrained to Research only:

1. Submit "Create a market intelligence report" (per `CCBP`'s Definition of Done example).
2. Confirm COO analyzes the objective, creates a task, assigns Research Agent, executes, and returns output.
3. Confirm a COO Decision Record was written with reasoning, chosen action, and outcome.

**Exit criteria**: End-to-end objective → COO → single agent → output succeeds reproducibly. This is EIB's MVP Build Order Version 0.1.


## Phase 6 — Multi-Department Expansion — MVP Version 0.2

**Depends on**: Phase 5.

**Deliverables**:

- Engineering Agent and Compliance Agent activated (`departments/engineering`, `departments/compliance`, already scaffolded).
- Workflow Engine supporting multi-step, multi-department workflows (`EWOS` §10-14).
- Agent Registry now resolves capability requests across 3 agents.

**Test**: MVS Test Category 004 (COO Orchestration), using a two-department objective:

1. Submit an objective requiring both research and engineering capability.
2. Confirm the COO decomposes it into a workflow spanning Research → Engineering.
3. Confirm both agents' outputs are captured and sequenced correctly per their dependency.

**Exit criteria**: A workflow crossing two departments completes correctly, in the right order, without manual intervention. This is EIB's MVP Build Order Version 0.2.


## Phase 7 — Knowledge Graph + Full Roster — MVP Version 0.3

**Depends on**: Phase 6.

**Deliverables**:

- Knowledge Graph service (`EKGS`), wired to record entities and relationships produced by workflow execution.
- Review Agent and Operations Department activated — completes the MVS-canonical four-department roster.
- Risk-proportional review loop wired into workflows (`TDL` §17).

**Test**: MVS Test Categories 003 (Department Operation) and 006 (Knowledge Graph) together:

1. Submit an objective exercising all four departments: Research → Engineering → Compliance → Review.
2. Confirm Review Agent produces a pass/fail validation with documented reasoning.
3. Query the Knowledge Graph for the relationship `Agent USES Capability APPLIES_TO Workflow` created by this run and confirm it resolves correctly.

**Exit criteria**: A full four-department workflow completes with a review gate, and the resulting relationships are queryable in the Knowledge Graph. This is EIB's MVP Build Order Version 0.3.


## Phase 8 — Governance Completion — MVP Version 0.4

**Depends on**: Phase 7.

**Deliverables**:

- Compliance Intelligence Engine: applicability assessment per `ECRIS` §8 (Business Activity + Location + Data Type + Industry + Entity Type + Risk Profile → Applicability).
- Observability Platform: Enterprise Command Centre views for Director/COO/Department (`EOCCS` §21-24), alerting (`EOCCS` §25).
- Security monitoring completion: trust scoring, incident workflow (`ESTAS` §26-28).
- **Four-condition escalation policy** for ESTAS §10's Risk Assessment step, adopted from an external swarm design (Idea Lab) as a substitute for COOS §9's undefined numeric complexity/risk scoring (no such algorithm exists anywhere in the source corpus — see `planner.py`'s docstring). The COO escalates to a human — and only a human — when one of exactly four named conditions fires; everything else the COO resolves itself:
  1. Objective Understanding / Department Selection (COOS §7-9) yields no viable department match (`NoMatchingDepartmentError`, already raised in `controller.py`).
  2. Outcome Validation (`evaluator.py`, COOS §20) returns "objective not achieved."
  3. A quality/integrity gate (Review Agent's pass/fail, Phase 7's risk-proportional review loop, `TDL` §17) flags a result as superficial or incomplete despite nominally passing.
  4. A downstream department/agent in a multi-department workflow (Phase 6/7 Workflow Engine) hits a dependency or traceability gap it cannot resolve within its own capability/context.
  A technical failure (agent runtime exception, Model Gateway failure, output that fails RCS contract validation) always escalates too, but is logged as a technical failure, distinct from the four framework verdicts above — never conflate the two in the Decision Record.

**Test**: MVS Test Categories 008 (Compliance) and 009 (Observability), run as formal (not smoke) tests:

1. Introduce a new policy requirement; confirm impact analysis, workflow review, and control recommendation are generated (MVS §12).
2. Execute a workflow and confirm logs, metrics, traces, and performance data are all recorded (MVS §13).
3. Trigger each of the four escalation conditions independently (no matching department, failed outcome validation, a review gate flagging a superficial pass, an unresolvable cross-department dependency gap) and confirm each produces a human-escalation record, and that a separate technical-failure case (e.g. a forced Model Gateway exception) is logged as a technical failure rather than as one of the four.

**Exit criteria**: Both governance test categories pass without manual log inspection, and all four escalation conditions (plus the technical-failure path) are independently reproducible and correctly classified in the Decision Record. This is EIB's MVP Build Order Version 0.4.


## Phase 9 — MVP Validation — Version 1.0

**Depends on**: Phase 8.

**Deliverables**:

- The "Learn" step of COOS §6's Operating Cycle (memory promotion from outcomes), the one step `controller.py` has deliberately left unimplemented since Phase 5. Implemented as **tiered promotion**, not a single uniform gate, adopted from an external swarm design (Idea Lab) and adapted to reuse Phase 8's four-condition escalation policy rather than inventing a second, separate risk classification:
  - **Minor / incremental lessons** — outcomes from a workflow that completed without tripping any of Phase 8's four escalation conditions. Self-approved by the COO (the swarm's own decision-maker, already the author of the COOS §22 Decision Record) and written directly to the Historical tier as a new, self-contained memory object — never merged into or amending an existing one, so a bad auto-approval can't silently compound. Logged in the Decision Record as `promotion: auto-approved`.
  - **Critical lessons** — outcomes from a workflow where one of Phase 8's four escalation conditions fired (or a technical failure occurred). Not written to Historical tier automatically: held at Project/Department tier with an explicit pending-approval marker (a promotion-workflow concept, kept separate from `MemoryObject.validation_status`, which is EMAS's epistemic-confidence field, not an approval-state field — conflating the two would repeat the tier/domain naming collision fixed in Phase 2) until a human approves or rejects. The COO continues normal Business-As-Usual operation on other objectives while a promotion is pending — approval is asynchronous and never blocks the orchestrator.
  - **Fallback rule, to be honored without hesitation if evidence during Phase 9 testing warrants it**: if the minor/critical split is found to add material complexity, produce promotion errors, or introduce project-specific bias into Historical-tier (enterprise-wide) memory, revert to human-approval-only for *all* Historical-tier promotions, minor or critical. Auto-approval of minor lessons is a not-yet-earned optimization — it gets re-enabled only once minor-lesson promotions have a track record showing alignment with the framework and no measurable complexity, error rate, or bias regression. Document whichever mode is active in `technology_decisions.md`, not silently.

**Test**: The full MVS acceptance suite, Test Categories 001–010, executed end to end:

- 001 Objective Execution, 002 Agent Lifecycle, 003 Department Operation, 004 COO Orchestration, 005 Memory Validation (run the same task type twice, confirm the second run improves via stored knowledge — for this phase, additionally confirm a minor-lesson outcome is auto-promoted and a critical-lesson outcome is held pending human approval, with BAU execution unaffected on both paths), 006 Knowledge Graph, 007 Security, 008 Compliance, 009 Observability, 010 Failure Recovery (disable a component, confirm detection → alert → recovery → resumption).

**Exit criteria**: All ten MVS test categories pass, including the tiered Learn step's minor/critical split behaving as designed. Per MVS §19, The Company is operational: it can receive objectives, organise itself, execute work, remember outcomes, improve safely, and operate under governance. Test Category 011 (Evolution) is explicitly out of scope here — it requires Phase 11.


## Phase 10 — Expansion Layer (post-MVP)

**Depends on**: Phase 9 (MVS acceptance passed).

**Deliverables**: SDK (agent/workflow/capability builders), Plugin system, Marketplace, external-facing API layer — per `EIB` Phase 3 and the Tier 4 documents (`EAAS`, `EPAS`, `ESDKS`, `EMAS`-marketplace).

**Test**: Use the SDK to define a new agent (not one of the original four) without editing core runtime code; confirm it registers in the Agent Registry and executes a task successfully through the existing COO/workflow path from Phases 5-7.

**Exit criteria**: A new agent can be added through the SDK alone. The Company can expand itself systematically (EIB Phase 3 completion criterion).


## Phase 11 — Intelligence Systems (post-MVP)

**Depends on**: Phase 9. Independent of Phase 10 (may be built in parallel with it).

**Deliverables**: Digital Twin state synchronization, Simulation Framework, Evolution Engine improvement-proposal pipeline — per `ESDTS` and `EESIS`.

**Test**: MVS Test Category 011 (Evolution Validation):

1. Introduce a deliberately inefficient workflow.
2. Confirm the Evolution Engine detects the inefficiency, requests a simulation, and produces an improvement proposal.
3. Confirm the proposal requires explicit approval before being applied — the Evolution Engine cannot self-approve changes (`EESIS` §10, `ESTAS` §21).

**Exit criteria**: The full loop (Observation → Evolution Engine → Simulation → Recommendation → Approval → Implementation) completes for at least one real inefficiency, with human approval enforced as a hard gate.


---

## Notes on scope discipline

- Phases 0–4 intentionally contain **no orchestration and no multi-agent behaviour** — they
  validate the substrate (identity, memory, communication, single-agent execution) in
  isolation, so failures in later phases can be localized instead of requiring a full-stack
  debug.
- The department/agent activation order (Research → Engineering+Compliance → Review) follows
  `FATS` §10's reasoning under MVS-canonical department naming, not `EIB`'s alternative
  reasoning-first ordering — both are valid; this plan picked the one that lets Phase 6 test
  cross-department coordination before Phase 7 adds the review gate, which is a cleaner
  testing progression.
- Nothing in Phases 0–9 should require touching Tier 4 (`Specifications/4 -
  future-expansion/`) — if an implementer finds themselves needing SDK, Plugin, Marketplace,
  or compiler-track content before Phase 10, that's a signal the phase boundary has been
  violated.
