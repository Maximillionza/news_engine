# The Company — Milestone-Based Implementation Plan

Version 1.0, synthesizing the build sequences already defined across `Specifications/2 - construction-framework/Enterprise Implementation Blueprint (EIB).md`, `Specifications/3 - execution-framework/AI Builder Master Execution Package (ABMEP).md`, and `Specifications/3 - execution-framework/MVP Validation Specification (MVS).md` into one concrete, testable sequence.

**Status note (reconciled 2026-07-23, PRD `Documentation/plans/2026-07-23-closing-the- crewai-capability-gap-prd.md` initiative 5.1):** this document previously stated "No code has been written against this plan — it is a planning artifact only." That was false and had drifted badly out of date. As of this reconciliation, all twelve phases have real, substantially-implemented code and passing tests - see the status table below. This reconciliation is a repo-state check (do the files and tests described by each phase's deliverables exist and pass), not a line-by-line re-audit of every exit-criteria bullet - treat "Implemented" below as strong evidence, not a formal phase sign-off.

## How to read this document

Twelve phases. Each phase has:

- **Depends on** — which prior phases must be *done* (not just started) before this one can begin.

- **Deliverables** — what gets built, named against the repository structure already scaffolded (`agents/`, `services/`, `departments/`, etc.).

- **Test** — how this phase is validated **on its own**, without needing any later phase to exist. This is the hard requirement: if a phase's test can only pass once a future phase is also built, the phase boundary is wrong and should be redrawn.

- **Exit criteria** — the observable state that means "this phase is done."

Phases 0–9 constitute the MVS-canonical MVP (Director + COO + Research/Engineering/ Compliance/Operations departments + one agent each + full governance layer). Phases 10–11 are explicitly post-MVP, per EIB Phase 3/4 and CCBP §10 ("First Expansion After MVP"). Phases 12 onward (added 2026-07-23, see "Phase 12 and beyond" below) are this document's single source of truth for what's built vs. what's next, superseding the standalone `Documentation/plans/2026-07-23-closing-the-crewai-capability-gap-prd.md` for status tracking — that document's reasoning/evidence stays valid, its initiatives now live here as numbered phases instead, so status isn't tracked in two places.

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
          │  
          ├── Phase 12  Agent tool-calling  
          ├── Phase 13  Failure & load resilience testing  
          ├── Phase 15  Intake sufficiency-check coverage extension  
          │      │  
          │      └── Phase 16  Department Head direct execution + specialist spawning  
          │             │  
          │             └── Phase 17  Specialist spawn ledger + Evolution promotion heuristic  
          │                    │  
          │                    └── Phase 19  Enterprise Compiler / CEDL (long-horizon)  
          │  
          Phase 12 ──→ Phase 14  Operational dogfooding ──→ Phase 18  Department creation (deferred)
          │
          ├── Phase 20  Cost/complexity-aware execution mode (Lean/Fast)
          ├── Phase 21  Inter-department task delegation ──→ recommended before/alongside Phase 18
          ├── Phase 22  Artifact pre-assessment + direction confirmation
          └── Phase 23  Skill/tool effectiveness memory (needs Phase 14 signal)
```

No phase may begin before its predecessor's exit criteria are met. This mirrors the Build Dependencies chain in EIB §12 (Identity → Security → Runtime → Agents → Workflows → Departments → Expansion Systems).

## Actual status (reconciled 2026-07-23)

Full test suite: **266 passed, 4 skipped** (`python -m pytest`). The 4 skipped are all gated live-credential smoke tests (real Claude API/Agent SDK calls, opt-in via env var), not failures or missing coverage. The MVS acceptance suite (`Tests/acceptance/ test\_mvs\_acceptance.py`) covers all 10 of Phase 9's categories in one file (13 test methods) and passes in full - this is Phase 9's own exit criteria, met.

| Phase | Name | Status | Evidence |
| - | - | - | - |
| 0 | Foundation & Contracts | Implemented | `services/shared/contracts.py` defines `RequestContract`/`ResponseContract`/`EventContract`/`ServiceContract`; `GET /health` exists in `apps/api\_gateway/main.py`. |
| 1 | Identity & Security Core | Implemented | `services/identity\_service/\{models,repository\}.py`; `services/security\_service/\{permissions,audit,trust,incidents\}.py`. |
| 2 | Data Layer & Memory Substrate | Implemented | `services/memory\_service/models.py` defines the five-tier `MemoryTier` enum (working/project/department/enterprise/historical) matching EMAS. |
| 3 | Runtime & Communication Backbone | Implemented | `services/event\_service/bus.py`, `services/shared/service\_bus.py`. |
| 4 | Agent Runtime (single agent) | Implemented | `services/agent\_runtime/\{runtime,registry\}.py`; `ModelGateway` (`services/shared/model\_gateway.py`) is the sole permitted path to a provider, enforced by an integration test. |
| 5 | COO + Single Department (MVP v0.1) | Implemented | `services/orchestrator/\{controller,classification,allocator\}.py`. |
| 6 | Multi-Department Expansion (MVP v0.2) | Implemented | `services/workflow\_engine/engine.py::execute\_workflow`. |
| 7 | Knowledge Graph + Full Roster (MVP v0.3) | Implemented | `services/knowledge\_service/\{models,repository\}.py`; `agents/active/` has all four department agents plus `review\_agent`. |
| 8 | Governance Completion (MVP v0.4) | Implemented | `services/orchestrator/escalation.py::EscalationCondition` (the four-condition policy) and `escalations.py` (persistence); `services/observability\_service/\{telemetry,alerting,views\}.py`. |
| 9 | MVP Validation (v1.0) | Implemented | `services/memory\_service/promotion.py` (minor/critical tiered promotion); full MVS 001-010 acceptance suite passing (see above). |
| 10 | Expansion Layer (post-MVP) | Implemented | `sdk/\{agent,workflow,capability,plugin\}\_builder/`; `services/plugin\_service/`, `services/marketplace\_service/`; tested in `Tests/integration/test\_plugin\_service.py`, `test\_marketplace\_service.py`. |
| 11 | Intelligence Systems (post-MVP) | Implemented | `services/evolution\_service/pipeline.py`, `services/digital\_twin\_service/`, `services/simulation\_service/workflow\_simulation.py`; `Tests/integration/test\_evolution\_engine.py::TestEvolutionValidationMVS011` (named directly after MVS Test Category 011), `test\_digital\_twin\_and\_simulation.py`. |
| 12 | Agent Tool-Calling | Implemented (2026-07-23) | Per-agent `allowed_tools` threaded from `agent.yaml`'s `tools.available` through `AgentRuntime` -> `ModelGateway` -> `AgentSDKModelProvider`, with tool-use events now visible in telemetry. Research's `WebSearch` shipped; Engineering's code-execution tool deliberately deferred (no bash sandboxing on Windows - see Engineering note below). 296 tests passing, 4 skipped, unchanged. |
| 13 | Failure & Load Resilience Testing | Implemented (2026-07-23), (3) manual | Deliverables (1), (2), (4) automated and committed; (3) documented as a manual runbook per its own exit criteria (real credentials/cost, matching this project's live-test precedent). **Bottleneck finding: not a real constraint** - concurrent `/chat/sync` calls genuinely overlap rather than serialize, measured directly (5 concurrent 0.3s-delay calls completed in ~0.4-0.5s, not the ~1.5s full serialization would produce), reproduced 3x. 299 tests passing, 4 skipped. |
| 14 | Operational Dogfooding | Process started (2026-07-23), inherently never "complete" | `Documentation/operations/dogfooding_log.md` - tracking mechanism and review process ready. The actual dogfooding (submitting real objectives, reviewing Decision Records) needs the user's own credentials and business judgment, same as every other live/gated activity this session - handed off, not run by the agent. |
| 15 | Intake Sufficiency-Check Coverage Extension | Implemented (2026-07-23) | `apps/api_gateway/dashboard_api.py::chat_send_sync` now runs the same sufficiency gate as `chat_send`; `apps/api_gateway/main.py::submit_objective` runs a single-shot (no round-loop) version, since `/objectives` has no conversation state to count rounds against. 272 tests passing, 4 skipped (same gated live-credential tests as before), including 5 new tests covering the insufficient/third-round/rejection paths on both endpoints. |
| 16 | Department Head Direct Execution + Specialist Spawning | Implemented (2026-07-23) | `orchestrator/head.py::resolve_verdict_execution()` (shared mechanism), wired into both `controller.py` (single-department) and `workflow_engine.py` (multi-department); `LLMDepartmentHead` now attempts objectives directly. All four head agent.yaml files updated. 282 tests passing, 4 skipped, zero changes to any pre-existing test (full backward compatibility confirmed). |
| 17 | Specialist Spawn Ledger + Evolution Promotion Heuristic | Implemented (2026-07-23) | `orchestrator/spawns.py` (ledger), `evolution_service/detection.py::detect_specialist_pattern()`, `evolution_service/pipeline.py::EvolutionEngine.propose_specialist_agent()` + `create_agent` actuation in `implement_change()`. "Create department" proposal type deliberately excluded - depends on undelivered Phase 18. 290 tests passing, 4 skipped, unchanged. |
| — | Department Creation Capability | Deferred | No phase/priority assigned yet —Priority: **Low, deliberately deferred** until Phase 14 produces real case data. |
| — | Enterprise Compiler / CEDL (multi-company generation) | Long-horizon | No phase/priority assigned yet —Not scoped. Depends on Phase 17's small-scale self-improvement loop earning a track record first. |
| — | EEOS (Economics & Optimization) | Needs exploration | No phase/priority assigned yet — scope this before scheduling it. |
| — | EDIS (Deployment & Infrastructure) | Not a gap | `Infrastructure/`'s empty scaffolding is correct as-is — purpose-built to stay empty until the Company has real operational/project history (Phase 14). Revisit then, not before. |
| — | EHCAS §13 "Decision Authority Class" | Resolved | Superseded by Phase 8's escalation policy (`orchestrator/escalation.py::EscalationCondition`) — no separate work needed. |
| 20 | Cost/Complexity-Aware Execution Mode (Lean/Fast) | Implemented (2026-07-26), parallel execution deliberately deferred | `workflow_engine/complexity.py` (real producer, replaces the old fixed "Level 2 Standard"), `orchestrator/execution_mode.py` (Lean/Fast), per-call `model` override threaded through `ModelGateway` -> both real providers -> `AgentRuntime.execute_task()` -> `dispatch()` -> `orchestrator/head.py`. Parallel department dispatch NOT built - `execute_workflow()`'s single shared SQLAlchemy `Session` isn't thread-safe, and building real concurrency needs a session-per-department redesign first (see Phase 20 detail section). 333 tests passing (24 new), 4 skipped. |
| 21 | Inter-Department Task Delegation | Implemented (2026-07-25) | `orchestrator/head.py`'s `HeadVerdict.needs_department_help` + `_resolve_department_delegation()`; `orchestrator/delegations.py` (ledger, mirrors Phase 17's spawns.py); `LLMDepartmentHead` prompt now offers a fourth outcome with explicit "prefer resolving in-domain work yourself" guidance. Unbounded delegation depth (per the founder's choice over a one-hop cap), made safe by a chain-membership cycle check rather than a fixed limit. 309 tests passing (10 new), 4 skipped. |
| — | Artifact Pre-Assessment & Direction Confirmation | Not started (2026-07-25) | Priority: Medium. See Phase 22 below. |
| — | Skill/Tool Effectiveness Memory | Not started (2026-07-25) | Priority: Medium-low, needs Phase 14 signal first. See Phase 23 below. |


Full detail for Phases 12-19 (deliverables, test approach, open questions) is in "Phase 12 and beyond" below, in the same format as Phases 0-11 above. Phases 20-23 (vision-comparison findings, 2026-07-25) follow immediately after Phase 19.


## Phase 0 — Foundation & Contracts

**Depends on**: nothing (repository structure and configuration templates already exist — see `CRBS`, `agents/templates/agent\_template.yaml`, `Configuration/company.yaml`).

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- Development environment (Python, FastAPI, PostgreSQL, per `EIAS` §4-8 and `CCBP` §6) — buildable and runnable, no application logic yet.

- `RCS`'s Universal Request Contract, Universal Response Contract, Event Contract, and Service Contract implemented as validated schemas (JSON Schema / Pydantic models), per RCS Principle 004 "contracts before implementation."

- `documentation/technology\_decisions.md` recording the concrete stack choices.

**Test**: A schema-validation test suite loads each contract schema and validates a hand-written example payload against it (one valid, one deliberately invalid per contract type, expecting rejection). The dev environment builds and serves a placeholder health-check endpoint.

**Exit criteria**: All four RCS contract schemas exist, are validated by an automated test, and no application code depends on anything beyond these schemas and the running dev environment.

## Phase 1 — Identity & Security Core

**Depends on**: Phase 0 (contracts exist to shape identity/security\_context payloads).

**Actual status: Implemented** — see the status table above.

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

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- Operational database, vector store, graph store, object storage provisioned (`EIAS` §8).

- Memory service implementing the canonical five-tier hierarchy — Working, Project, Department, Enterprise, Historical (`EMAS` §5, `memory/schemas/memory\_object\_template.yaml`).

- Knowledge object storage (entities/relationships tables), not yet wired to any graph query engine.

**Test**: Memory CRUD test suite, run without any agent runtime:

1. Write a memory object to each of the five tiers.

2. Retrieve it and confirm all EMAS-required fields persisted (context, confidence, validation\_status, applicability, expiration).

3. Confirm tier isolation: a Project-tier memory written under Project A is not returned when querying Project B's context (`EMAS` §13 Context Filtering).

**Exit criteria**: All five tiers support write/read, and the isolation test demonstrates no cross-project leakage.

## Phase 3 — Runtime & Communication Backbone

**Depends on**: Phase 0 (contracts), Phase 1 (security\_context is mandatory on every message per `RCS` §6).

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- Service framework hosting the API Gateway (`services/orchestrator` scaffolding already exists).

- Event Bus and Service Bus implementations (`services/event\_service`, per `EEBS`/`ESBS` design in Tier 4 — implemented now since core communication is MVP-critical, unlike the SDK/Plugin/Marketplace layer those documents also describe).

- Structured logging and telemetry emission (`EOCCS` §6 Enterprise Telemetry Model).

**Test**: Synthetic producer/consumer test, no real agents:

1. A test service registers on the Service Bus and responds to a request using the RCS Universal Request/Response Contract.

2. A test event is published on the Event Bus and received by a subscribed test consumer.

3. Both actions appear in telemetry with correct component/action/timestamp/duration fields.

**Exit criteria**: Synthetic request-response and publish-subscribe both succeed, both produce telemetry, and both carry a valid security\_context validated in Phase 1.

## Phase 4 — Agent Runtime (single agent, no orchestration)

**Depends on**: Phase 2 (memory access), Phase 3 (communication, telemetry).

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- Agent Runtime engine implementing the Agent Execution Cycle: Receive Task → Load Context → Retrieve Knowledge → Check Policies → Plan → Execute → Validate → Produce Artifact → Report Outcome → Release Context (`ROM` §11).

- Agent Registry (`agents/active/`, already scaffolded with `research\_agent`, `engineering\_agent`, `compliance\_agent`, `review\_agent` templates).

- Model Gateway routing stub — may route to a single model provider initially; the abstraction (`Agent → Model Gateway → Selected Model`, per `RDL` §11 / `EIAS` §11) must exist even if the routing logic is trivial.

**Test**: Load `research\_agent/agent.yaml`, issue one canned task directly to the Agent Runtime (bypassing the COO entirely), and confirm:

1. The agent runtime traverses all nine Agent Execution Cycle steps (observable via telemetry from Phase 3).

2. Output is produced and an audit record exists (Phase 1).

3. The agent never calls a model directly — only through the Model Gateway.

**Exit criteria**: One agent runs a task end-to-end without a COO in the loop, and the model-abstraction rule is verifiably enforced (test fails if the agent's code path bypasses the gateway).

## Phase 5 — COO + Single Department — MVP Version 0.1

**Depends on**: Phase 4.

**Actual status: Implemented** — see the status table above.

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

**Actual status: Implemented** — see the status table above.

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

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- Knowledge Graph service (`EKGS`), wired to record entities and relationships produced by workflow execution.

- Review Agent and Operations Department activated — completes the MVS-canonical four-department roster.

- Risk-proportional review loop wired into workflows (`TDL` §17).

**Test**: MVS Test Categories 003 (Department Operation) and 006 (Knowledge Graph) together:

1. Submit an objective exercising all four departments: Research → Engineering → Compliance → Review.

2. Confirm Review Agent produces a pass/fail validation with documented reasoning.

3. Query the Knowledge Graph for the relationship `Agent USES Capability APPLIES\_TO Workflow` created by this run and confirm it resolves correctly.

**Exit criteria**: A full four-department workflow completes with a review gate, and the resulting relationships are queryable in the Knowledge Graph. This is EIB's MVP Build Order Version 0.3.

## Phase 8 — Governance Completion — MVP Version 0.4

**Depends on**: Phase 7.

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- Compliance Intelligence Engine: applicability assessment per `ECRIS` §8 (Business Activity + Location + Data Type + Industry + Entity Type + Risk Profile → Applicability).

- Observability Platform: Enterprise Command Centre views for Director/COO/Department (`EOCCS` §21-24), alerting (`EOCCS` §25).

- Security monitoring completion: trust scoring, incident workflow (`ESTAS` §26-28).

- **Four-condition escalation policy** for ESTAS §10's Risk Assessment step, adopted from an external swarm design (Idea Lab) as a substitute for COOS §9's undefined numeric complexity/risk scoring (no such algorithm exists anywhere in the source corpus — `planner.py`'s docstring made this point originally; the same fixed-default honesty note now lives in `controller.py`, since that logic was relocated). The COO escalates to a human — and only a human — when one of exactly four named conditions fires; everything else the COO resolves itself:

  1. Objective Understanding / Department Selection (COOS §7-9) yields no viable department match (`NoMatchingDepartmentError`, already raised in `controller.py`).

  2. Outcome Validation (`evaluator.py`, COOS §20) returns "objective not achieved."

  3. A quality/integrity gate (Review Agent's pass/fail, Phase 7's risk-proportional review loop, `TDL` §17) flags a result as superficial or incomplete despite nominally passing.

  4. A downstream department/agent in a multi-department workflow (Phase 6/7 Workflow Engine) hits a dependency or traceability gap it cannot resolve within its own capability/context. A technical failure (agent runtime exception, Model Gateway failure, output that fails RCS contract validation) always escalates too, but is logged as a technical failure, distinct from the four framework verdicts above — never conflate the two in the Decision Record.

**Test**: MVS Test Categories 008 (Compliance) and 009 (Observability), run as formal (not smoke) tests:

1. Introduce a new policy requirement; confirm impact analysis, workflow review, and control recommendation are generated (MVS §12).

2. Execute a workflow and confirm logs, metrics, traces, and performance data are all recorded (MVS §13).

3. Trigger each of the four escalation conditions independently (no matching department, failed outcome validation, a review gate flagging a superficial pass, an unresolvable cross-department dependency gap) and confirm each produces a human-escalation record, and that a separate technical-failure case (e.g. a forced Model Gateway exception) is logged as a technical failure rather than as one of the four.

**Exit criteria**: Both governance test categories pass without manual log inspection, and all four escalation conditions (plus the technical-failure path) are independently reproducible and correctly classified in the Decision Record. This is EIB's MVP Build Order Version 0.4.

## Phase 9 — MVP Validation — Version 1.0

**Depends on**: Phase 8.

**Actual status: Implemented** — see the status table above.

**Deliverables**:

- The "Learn" step of COOS §6's Operating Cycle (memory promotion from outcomes), the one step `controller.py` has deliberately left unimplemented since Phase 5. Implemented as **tiered promotion**, not a single uniform gate, adopted from an external swarm design (Idea Lab) and adapted to reuse Phase 8's four-condition escalation policy rather than inventing a second, separate risk classification:

  - **Minor / incremental lessons** — outcomes from a workflow that completed without tripping any of Phase 8's four escalation conditions. Self-approved by the COO (the swarm's own decision-maker, already the author of the COOS §22 Decision Record) and written directly to the Historical tier as a new, self-contained memory object — never merged into or amending an existing one, so a bad auto-approval can't silently compound. Logged in the Decision Record as `promotion: auto-approved`.

  - **Critical lessons** — outcomes from a workflow where one of Phase 8's four escalation conditions fired (or a technical failure occurred). Not written to Historical tier automatically: held at Project/Department tier with an explicit pending-approval marker (a promotion-workflow concept, kept separate from `MemoryObject.validation\_status`, which is EMAS's epistemic-confidence field, not an approval-state field — conflating the two would repeat the tier/domain naming collision fixed in Phase 2) until a human approves or rejects. The COO continues normal Business-As-Usual operation on other objectives while a promotion is pending — approval is asynchronous and never blocks the orchestrator.

  - **Fallback rule, to be honored without hesitation if evidence during Phase 9 testing warrants it**: if the minor/critical split is found to add material complexity, produce promotion errors, or introduce project-specific bias into Historical-tier (enterprise-wide) memory, revert to human-approval-only for *all* Historical-tier promotions, minor or critical. Auto-approval of minor lessons is a not-yet-earned optimization — it gets re-enabled only once minor-lesson promotions have a track record showing alignment with the framework and no measurable complexity, error rate, or bias regression. Document whichever mode is active in `technology\_decisions.md`, not silently.

**Test**: The full MVS acceptance suite, Test Categories 001–010, executed end to end:

- 001 Objective Execution, 002 Agent Lifecycle, 003 Department Operation, 004 COO Orchestration, 005 Memory Validation (run the same task type twice, confirm the second run improves via stored knowledge — for this phase, additionally confirm a minor-lesson outcome is auto-promoted and a critical-lesson outcome is held pending human approval, with BAU execution unaffected on both paths), 006 Knowledge Graph, 007 Security, 008 Compliance, 009 Observability, 010 Failure Recovery (disable a component, confirm detection → alert → recovery → resumption).

**Exit criteria**: All ten MVS test categories pass, including the tiered Learn step's minor/critical split behaving as designed. Per MVS §19, The Company is operational: it can receive objectives, organise itself, execute work, remember outcomes, improve safely, and operate under governance. Test Category 011 (Evolution) is explicitly out of scope here — it requires Phase 11.

## Phase 10 — Expansion Layer (post-MVP)

**Depends on**: Phase 9 (MVS acceptance passed).

**Actual status: Implemented** — see the status table above.

**Deliverables**: SDK (agent/workflow/capability builders), Plugin system, Marketplace, external-facing API layer — per `EIB` Phase 3 and the Tier 4 documents (`EAAS`, `EPAS`, `ESDKS`, `EMAS`-marketplace).

**Test**: Use the SDK to define a new agent (not one of the original four) without editing core runtime code; confirm it registers in the Agent Registry and executes a task successfully through the existing COO/workflow path from Phases 5-7.

**Exit criteria**: A new agent can be added through the SDK alone. The Company can expand itself systematically (EIB Phase 3 completion criterion).

## Phase 11 — Intelligence Systems (post-MVP)

**Depends on**: Phase 9. Independent of Phase 10 (may be built in parallel with it).

**Actual status: Implemented** — see the status table above.

**Deliverables**: Digital Twin state synchronization, Simulation Framework, Evolution Engine improvement-proposal pipeline — per `ESDTS` and `EESIS`.

**Test**: MVS Test Category 011 (Evolution Validation):

1. Introduce a deliberately inefficient workflow.

2. Confirm the Evolution Engine detects the inefficiency, requests a simulation, and produces an improvement proposal.

3. Confirm the proposal requires explicit approval before being applied — the Evolution Engine cannot self-approve changes (`EESIS` §10, `ESTAS` §21).

**Exit criteria**: The full loop (Observation → Evolution Engine → Simulation → Recommendation → Approval → Implementation) completes for at least one real inefficiency, with human approval enforced as a hard gate.


## Phase 12 and beyond — Post-Reconciliation Roadmap (added 2026-07-23)

Unlike Phases 0-11, these phases weren't synthesized from the Tier 1-3 specification corpus

- they came out of a direct architecture review against CrewAI and a codebase-grounded discussion of self-organization concepts, both on 2026-07-23. Same format as above (Depends on / Deliverables / Test / Exit criteria) where the work is scoped enough to support it; phases still needing scoping say so plainly instead of inventing false precision.

### Phase 12 — Agent Tool-Calling

**Depends on**: Phase 4 (Agent Runtime), Phase 10 (SDK).

**Priority: High.**

**Actual status: Implemented (2026-07-23), Research only.** Engineering's code-execution
tool was scoped out after checking the Claude Agent SDK directly: `SandboxSettings.enabled`
is explicitly macOS/Linux only, so on this Windows machine there is no sandboxing available
at all - giving Engineering raw shell access would mean genuinely unrestricted command
execution during autonomous reasoning, not the "sandboxed" tool this phase's deliverables
originally assumed. Deferred rather than shipped unsafely; revisit with a real constrained
design (a narrow `can_use_tool` command allowlist, or a real sandbox if this ever runs on
Linux/macOS) before wiring it. Compliance's tool is similarly not yet scoped.

The real architectural finding: before this phase, there was exactly one shared
`ModelProvider` instance for the entire swarm, constructed once with a fixed `allowed_tools`
- nothing about a call identified which agent/department was asking, so per-department tools
literally could not be expressed. Fixed by threading tool selection through the existing
per-call path instead of introducing multiple provider instances: `AgentDefinition.tools`
(present in the schema since Phase 4, previously read by nothing - `agent_runtime/
registry.py`'s own docstring called it out as having zero runtime effect) now actually
matters - `AgentRuntime`'s Execute step reads `self.agent.tools.get("available", [])` and
passes it through `ModelGateway.generate(..., allowed_tools=...)` to
`AgentSDKModelProvider.generate()`, which lets the per-call value override its own
constructor-level default. `StubModelProvider` and `AnthropicModelProvider` accept and ignore
it (Protocol compatibility; the raw Messages API path has no tool-use concept to wire this
into). `research_agent/agent.yaml`'s `tools.available` was populated with the real SDK tool
name (`WebSearch`) - it previously held `[search, document_processing]`, placeholder values
that were never real tool names and would have been silently unrecognized.

Tool-use visibility (the actual exit criterion) required `AgentSDKModelProvider` to gain an
optional `telemetry` sink, threaded from `main.py` through `create_provider_from_env()` -
`_default_runner` now inspects `AssistantMessage.content` for `ToolUseBlock`/
`ServerToolUseBlock` entries mid-stream (the only place a tool invocation is ever observable;
the terminal `ResultMessage` only carries final text) and records a `tool_use:{name}` event
per call.

**Engineering department, flagged not resolved:** deferred per above - no department agent
uses it yet.

**Shared-connection bottleneck - raised by the user, not yet answered:** while investigating
per-agent tool scoping, it became clear there is no queueing or locking at the model-provider
layer for concurrent synchronous calls (`/chat/sync`, `/objectives` - the async `/chat` queue
processes strictly sequentially, one worker, confirmed by `queue_worker.py`'s own docstring).
Whether the single shared `ModelProvider` instance is an actual bottleneck under real
concurrent load - and whether the swarm's own stated goal of "multiple departments reasoning
in parallel" is even achievable with this architecture - is genuinely untested. Tracked as
part of Phase 13's scope below rather than answered here: Phase 13's concurrent-objective
test is exactly the evidence needed before this becomes an update plan worth raising.

12 new/modified tests across `test_agent_sdk_provider.py` (per-call override, telemetry
recording, real message-stream tool-block detection) and a new end-to-end test in
`test_agent_runtime.py` proving `research_agent/agent.yaml`'s real on-disk `tools.available`
value reaches the provider, not just plumbing that compiles. Every pre-existing fake
`ModelProvider` test double across the suite needed a mechanical `allowed_tools=None`
parameter addition (`ModelGateway.generate()` now always passes it) - a wide but shallow
blast radius, confirmed by all pre-existing tests passing unmodified in behavior.

**Deliverables**: `AgentSDKModelProvider`'s `allowed\_tools` mechanism already exists and is wired into the Claude Agent SDK's own tool loop - it has simply never been populated. Wire one real tool per department, matched to its actual mission: Research gets a web-search tool, Engineering gets a sandboxed code-execution/lint/test-runner tool, Compliance gets a policy/document-lookup tool. Do not build a general-purpose tool library up front - that's explicitly out of scope (see the CrewAI-gap PRD's non-goals).

**Test**: At least one department agent completes a real objective requiring an external tool call mid-reasoning, with that call visible in `observability\_service/telemetry.py` - not just inferable from the final text output.

**Exit criteria**: One department agent demonstrably uses its tool in a real (non-test) objective, logged in telemetry.

### Phase 13 — Failure & Load Resilience Testing

**Depends on**: Phase 9 (objective queue, escalation policy).

**Priority: High.**

**Actual status: Implemented (2026-07-23), deliverable (3) is a manual runbook, not
automated code - matches its own exit criteria and this project's precedent for live/gated
tests.** Deliverable (2)'s existing pre-Phase-13 tests (`test_escalation_policy.py`) turned
out to only cover a provider that fails on the very first call - never a genuine mid-workflow
failure with real completed work behind it. A new test with a provider that succeeds once
then fails found a real, pre-existing gap made visible for the first time: department 1's
knowledge-graph entries survive a later department's failure, but the COO Decision Record's
`agents_selected`/`outcome` fields don't reflect that any work happened at all - identical to
what a zero-progress failure produces. Not fixed here (out of this phase's charter), just
verified and documented precisely rather than assumed.

Deliverable (4) (the user's bottleneck question from Phase 12) has a clear, reproduced
answer: **not a real constraint.** A deliberately slow fake provider
(`Tests/integration/test_concurrent_load.py`) makes serialization directly observable via
wall-clock time - 5 concurrent `/chat/sync` requests, each with a 0.3s artificial delay,
completed in ~0.4-0.5s (close to the ~0.3s full-parallelism estimate), not the ~1.5s full
serialization would produce, reproduced identically across 3 runs. Nothing in
`ModelGateway`/`AgentSDKModelProvider` serializes concurrent calls - Python releases the GIL
during I/O waits, and neither holds a lock. Caveat: this measures a simulated I/O-bound delay
(`time.sleep()`), not the real `AgentSDKModelProvider`'s actual subprocess/IPC behavior under
concurrent load, which needs live credentials and cost to verify directly - the mechanism
(both rely on I/O-bound waits releasing the GIL) makes the same result likely, not certain.
No architecture change recommended based on this evidence.

**Deliverables**: `Documentation/plans/SDK\_MIGRATION\_PLAN.md` Section 1 already flags shared subscription-usage-window contention as a real risk; nothing tests it. Three targeted tests, not full Phase 11 simulation scope: (1) N concurrent objectives through `queue\_worker.py` - no queue corruption, no lost/duplicated jobs; (2) a forced provider failure mid-workflow - confirms the technical-failure escalation path Phase 8 already defines fires correctly and is distinct from the four framework-verdict conditions; (3) one soak test over an extended run, confirming no resource leak or worker deadlock.



**Addition raised by the user (2026-07-23), during Phase 12:** (4) the shared-connection
bottleneck question - is the single `ModelProvider` instance (see Phase 12's own note above)
a real constraint under concurrent load? Test (1) above, as originally scoped, would NOT
actually answer this - `queue_worker.py` processes objectives strictly sequentially by
design (one worker, confirmed by its own docstring), so nothing reaches the provider
concurrently through that path at all. The real test is concurrent calls through the
*synchronous* paths (`/chat/sync`, `/objectives`), which skip the queue entirely and call the
orchestrator directly - that's where two requests could genuinely overlap at the provider
today. Deliverable: fire N simultaneous `/chat/sync` (or `/objectives`) requests, observe
whether they complete correctly and how long they take relative to running the same N
sequentially, and produce a concrete recommendation (bottleneck confirmed / not a real
constraint / needs architecture change) to raise with the user as an update plan - not just a
pass/fail test.

**Test**: Automated, committed tests for (1) and (2) at minimum; (3) documented even if run manually.

**Exit criteria**: Both (1) and (2) pass as committed tests.

**Manual runbook for (3), the soak test (not automated - real credentials, real cost, real
time, matching this project's established pattern of leaving live/gated tests to the user):**

1. Set real credentials: `CLAUDE_CODE_OAUTH_TOKEN` (subscription) or `ANTHROPIC_API_KEY`, and
   `MODEL_PROVIDER=agent_sdk` (or `anthropic`) in `.env`.
2. Start the API gateway (`python apps/api_gateway/main.py`) and the queue worker
   (`Scripts/run_queue_worker.py`) as two separate long-running processes.
3. Note each process's baseline memory (Windows Task Manager, or
   `Get-Process -Id <pid> | Select WorkingSet64`) right after startup.
4. Submit a steady trickle of real objectives over an extended window - e.g., one real
   objective every 5-10 minutes for 2-4 hours (or overnight) via `POST /chat` (the async
   path, so this also exercises the queue worker continuously, not just the gateway).
5. Periodically (every 30-60 minutes) recheck: (a) each process's memory - a steady climb
   with no plateau is a leak; (b) `GET /activity`'s `in_flight_objectives` - anything stuck
   in `executing` for far longer than a normal objective takes is a worker deadlock;
   (c) both processes are still alive and responsive (`GET /health`).
6. At the end: every submitted objective should be `completed` or `failed`, never stuck in
   `queued`/`executing`; memory in both processes should have plateaued, not grown
   unboundedly; no unhandled exception should have killed either process.
7. Record the outcome (pass/fail, and any memory/hang numbers observed) in this document's
   own status update the same way every other phase's evidence is recorded - this exit
   criterion is met by that record existing, not by an automated test.

### Phase 14 — Operational Dogfooding

**Depends on**: Phase 12 (enough real tool capability to make it worth running).

**Priority: Medium — ongoing once started, no end date, runs in parallel with later phases.**

**Actual status: Process started (2026-07-23), not "implemented" in the sense every other
phase used that word.** `Documentation/operations/dogfooding_log.md` sets up the tracking
mechanism (a log table matching this phase's own exit criteria columns) and the review
process (how to submit a real objective through Samaritan/dashboard/API, how to pull its
Decision Record, what to actually check - routing, escalation, memory promotion, not just
whether it returned output). No entries logged yet - that requires real credentials and real
objectives from the user, the same boundary every other live/gated activity this session
respected (the Agent SDK smoke test, the confirmation-gate verification, this document's own
Phase 9 Steps 2-4). This phase has no "done" state to reach; it stays open, generating
regression tests as real usage finds real problems.

**Deliverables**: A passing test suite proves the system handles scenarios its author anticipated; it doesn't prove what CrewAI's independent user base proves for free. Route a defined set of real (non-test) objectives through the swarm over time. Review every Decision Record produced - not just success/failure, but whether department routing, escalation, and memory promotion were actually correct. Convert every mistake found into a new regression test.

**Test**: N/A - this phase generates test cases, it doesn't consume a pre-written one.

**Exit criteria**: A running log of real objectives processed, each with its Decision Record reviewed, and at least one regression test added per incorrect behavior found. Also the data source for Phase 18's deferred department-creation work and for scoping real infrastructure needs (EDIS, currently correctly unscheduled - see the status table above).

### Phase 15 — Intake Sufficiency-Check Coverage Extension

**Depends on**: Phase 5 (COO). Builds on the existing `orchestrator/intake.py`.

**Priority: High — foundational. Phase 16's Head-spawning conditions depend on this holding** **across every entry point, not just one.**

**Actual status: Implemented (2026-07-23).** `POST /chat/sync` now runs the identical
sufficiency gate `POST /chat` already had, sharing the same `DashboardChatMessage` round-
counting and consolidation - no new infrastructure needed, since it already wrote into that
same table. `POST /objectives` got a single-shot version instead of the same round-based
loop: it's a stateless, structured endpoint with no persistent conversation to count rounds
against, so an insufficient objective returns 422 with the clarifying question as the
terminal response, not one step in a retry loop - the caller resubmits a more complete
request, same as the existing required-field 422 just above it in that handler. Three
existing `/objectives` tests that were actually about routing/no-match/rejection (not
sufficiency) now bypass the check via `monkeypatch`, matching the pattern
`test_chat_returns_502_when_sufficiency_check_raises` already established; a new dedicated
test covers the real (unbypassed) insufficient-request path for each endpoint.

**Deliverables**: `intake.py::assess\_sufficiency()` already does exactly this - checks whether an objective has enough detail before dispatch, and asks a bounded clarifying question if not (capped at 3 rounds). Its own docstring is explicit that it's wired to only one of three entry points: `POST /chat` (the dashboard). `POST /chat/sync` (what Samaritan's `dispatch\_to\_company()` actually calls) and `POST /objectives` (the formal API) skip it entirely. Extend the same sufficiency gate to both. Samaritan itself should not need to reason about objective completeness - per its own design, it's meant to leverage the swarm, not duplicate its judgment - so this belongs entirely on the swarm side.

**Test**: Submit a deliberately under-specified objective via `/chat/sync` and via `/objectives`; confirm each surfaces a clarifying-question path equivalent to what `/chat` already does today, rather than dispatching on incomplete information.

**Exit criteria**: All three entry points enforce the same completeness gate before an objective ever reaches a department.

### Phase 16 — Department Head Direct Execution + Specialist Spawning

**Depends on**: Phase 15 (the completeness gate must hold everywhere first - see below for why).

**Priority: Medium-High.**

**Actual status: Implemented (2026-07-23).** Resolved the two open forks from the design
checkpoint: a spawned specialist is realized as the Head's own already-authorized identity
adopting a specialized mission/capability set for one task (not a new registered identity -
AgentRuntime's Check Policies step denies unknown identities outright, and a genuinely new
per-spawn identity would reintroduce the persistent-registration cost this phase deliberately
avoided); spawning for genuine capacity reasons is recorded in the Decision Record's
reasoning/chosen_action, not a new Escalation Condition. Condition 1 (insufficient
information) does not spawn - a second agent has no context the first lacked, so it can't fix
an information deficit - it's folded into a rejection instead, distinguishable in its
reasoning text from a wrong-department reject, on the reasoning that Phase 15 should make it
rare and it firing often is a signal that gate has a gap, not that more headcount is needed.

Shipped as four increments, each independently tested and committed: (1) the `HeadVerdict`
contract gains `resolved_output`/`needs_specialist`, plus `orchestrator/head.py`'s shared
`resolve_verdict_execution()` and `controller.py`'s single-department wiring; (2) the same
helper reused in `workflow_engine.py`'s multi-department loop, per-department independence
confirmed; (3) `LLMDepartmentHead` rewritten to attempt the objective in the same dispatch()
call that judges department fit, fully backward compatible with the pre-Phase-16 JSON
response shape; (4) all four head `agent.yaml` files updated with the new mandate and the
explicit "not an information-deficit escape valve" boundary, capabilities expanded from
`[triage]` to each department's real capability set. `operations_head` documented with an
honest caveat: it isn't actually reachable through the current triage wiring at all -
`workflow_engine.py`'s review step never calls `head.evaluate()` for it - closing that gap is
separate, unstarted work.

282 tests passing, 4 skipped (unchanged gated live-credential tests), zero modifications to
any pre-existing test - the AutoAcceptDepartmentHead default and every existing
LLMDepartmentHead JSON response shape produce identical behavior to before this phase.

**Deliverables**: Today, `orchestrator/head.py`'s `DepartmentHead.evaluate()` is a pure accept/reject gate - it never executes work itself. Reframe it: a Head attempts execution directly, and spawns an additional (specialist) agent only when one of two explicit conditions holds:

1. The information/context provided does not give the Head enough to confidently judge whether more headcount is required.

2. The Head's own analysis of the work - however complete that analysis is - still falls short of what one agent can deliver.

Condition 1 is deliberately narrow, not a routine escape valve: insufficient information is an *intake defect* to fix upstream (Phase 15), not something a Head should be expected to absorb by guessing. This is a design principle, not just an implementation detail - it needs to be written down somewhere departments/agents can be held to it (a DOMS-adjacent documentation update, not only code), so "the Head didn't have enough to go on" stops being an acceptable justification for spawning once Phase 15 is in place.

This changes the `HeadVerdict` contract - today `\{accepted, reasoning, suggested\_department\_id\}` - to something that can carry either a direct result or a delegation, e.g. `\{resolved\_by: "head"|"specialist", output, escalation\_reason\}`. That ripples into the Decision Record schema and Phase 8's escalation classification: a Head that genuinely can't finish isn't the same event as the four existing conditions - it's arguably a fifth, not a variant of an existing one.

**Test**: Not yet fully specified - needs definition once the contract change above is implemented. At minimum: an objective sized for one agent completes via the Head alone with no spawn; an objective genuinely exceeding one agent's capacity triggers a spawn with a recorded reason matching condition 1 or 2 above, never neither.

**Exit criteria**: TBD at implementation time.

### Phase 17 — Specialist Spawn Ledger + Evolution Promotion Heuristic

**Depends on**: Phase 16 (spawning has to exist before its pattern can be tracked).

**Priority: Medium.**

**Actual status: Implemented (2026-07-23).** Scoped down from the original two proposal
types to one: "create department" needs Phase 18's builder, which doesn't exist and is
deliberately deferred (see Phase 18 below) - only "create dedicated agent" shipped.

Two increments. (1) `orchestrator/spawns.py`'s `SpecialistSpawnRecord` ledger, written from
inside `resolve_verdict_execution()` right after a specialist dispatch succeeds - required
threading a new `decision_id` parameter through `resolve_verdict_execution()`,
`execute_workflow()` (which never had one before), and `simulation_service/
workflow_simulation.py`'s sandboxed dry runs (a synthetic id, since a simulation has no real
Decision Record). (2) `detect_specialist_pattern()` reads that ledger for one department at a
time (the caller decides which, and when - nothing calls this automatically, matching
`detect_and_propose()`'s own precedent of never being invoked in production either, only in
tests) and, at or above a threshold (default 3), produces an `ImprovementOpportunity`.
`propose_specialist_agent()` turns that into a `ChangeProposal` with the new `action_type`/
`action_payload` fields (EESIS's literal Change Proposal Model has no notion of proposal
"type" at all - an honest extension) carrying an `sdk.agent_builder.AgentDraft`'s fields,
idempotent against an already-pending-or-implemented proposal for the same department. No
simulation step - unlike the review-skip proposal, there's no meaningful "run it both ways"
dry run for "would a dedicated agent do better than repeated spawning" with the simulation
infrastructure this corpus has; `simulation_run_id` is left `None`, which the schema already
allowed.

`implement_change()` now branches on `action_type`: `"create_agent"` calls the unmodified
`build_agent()` (schema validation, identity creation, permission grants, a real smoke-test
execution, live `AgentRegistry` registration) via four new optional keyword parameters that
every pre-Phase-17 proposal (`action_type` defaults to `"record_only"`) ignores entirely -
confirmed by all 5 pre-existing evolution engine tests passing with zero modification. Wired
through to the live dashboard API (`main.py` / `dashboard_api.py`'s `/proposals/{id}/implement`
endpoint) so this is reachable, not just unit-tested in isolation - matching the same
reachability the review-skip proposal type already has (which is to say, not automatically
triggered either; a human or future scheduler still has to call `propose_specialist_agent()`
itself, same as `detect_and_propose()`).

One unrelated fragility found and fixed along the way: `apps/api_gateway/api_gateway_dev.sqlite3`
is a gitignored, persistent local dev database with no migration path - `Base.metadata.create_all()`
only creates missing tables, it doesn't alter existing ones, so the `ChangeProposal` schema
change broke 4 tests against the stale on-disk file until it was deleted and let regenerate.
Not fixed architecturally (no migration system added - out of scope here), just flagging it:
any future SQLAlchemy model change will hit this same wall again.

7 new tests in `test_evolution_engine.py` cover the detection threshold, proposal creation and
idempotency, and the full propose-approve-implement loop actually registering a working new
agent (verified via a real `AgentRuntime` smoke test and an `agent.yaml` written to disk, not
mocked). 290 tests passing, 4 skipped (unchanged gated live-credential tests).

**Deliverables**: A historical record of every specialist spawned by a Department Head (Phase 16), tagged by specialization. A new Evolution Engine detection heuristic reading that ledger for a repeated need for the same specialization - note this is a genuinely different shape from `evolution\_service/detection.py`'s existing `detect\_inefficiencies()`, which is scoped to one decision at a time; this needs a periodic or cross-decision pass, not an inline per-decision check like today's only heuristic. Two new `ChangeProposal` types: create a dedicated agent (wired to `sdk/agent\_builder`'s already-working `build\_agent()` - schema-validates, creates identity, grants permissions, runs a real smoke-test execution, registers into the live `AgentRegistry`, no restart needed) and create a new department (needs Phase 18, since no equivalent builder exists yet). Also worth knowing going in: `evolution\_service/pipeline.py::implement\_change()` currently only ever writes a memory record saying a change was "approved and implemented" - it does not mutate any runtime behavior for any existing proposal type. Wiring "create agent" to actually call `build\_agent()` on approval is the first case of this pipeline doing real work, not an incremental addition to a pattern that already does.

**Test**: TBD at implementation time.

**Exit criteria**: TBD at implementation time.

### Phase 18 — Department Creation Capability

**Status: Deliberately deferred.**

**Priority: Low.**

**Deliverables**: An `sdk/department\_builder`, parallel to `agent\_builder`'s `build\_agent()`

- activating `orchestrator/department\_registry.py`'s `DepartmentDefinition.lifecycle\_state` field, which already defaults to `"proposed"` but is never read or enforced anywhere today.

**Why deferred**: not a technical blocker - a deliberate choice. The Company needs to process real cases first (Phase 14) before there's tangible information about which new department(s), if any, are actually necessary. Building this speculatively risks the same "a lot of surface area for one operator" problem already flagged in the CrewAI comparison. Revisit once Phase 14 has produced real signal, not before.

**Sequencing note (added 2026-07-25, vision-comparison session)**: Phase 21 (Inter-Department Task Delegation) touches the same "elastic company" surface as this phase - how departments relate to each other, not just how many exist. Building Phase 18 without Phase 21 already in place risks baking in an assumption (department boundaries are fixed once created, coordination only happens via the classifier's up-front fan-out) that Phase 21 then has to unwind. Recommend Phase 21 lands before or alongside Phase 18, regardless of which one is scheduled first chronologically.

### Phase 19 — Enterprise Compiler / CEDL (long-horizon)

**Depends on**: Phase 17 (the small-scale version of this same pattern needs a track record first).

**Status: Not scoped. Long-horizon.**

Source: `Specifications/4 - future-expansion/`'s Volumes XXXII (MCDP), XXXIII (EMMS), XXXIV (CEDLS), XXXVII (EBAS), and XXXVIII (ERAS) - no code exists against any of them today. These describe something categorically bigger than everything else in this document: a declarative language (CEDL) for defining an AI-native enterprise as data, compiled and provisioned by a generic Enterprise Compiler/Builder/Runtime - not a feature of this Company, but a platform for generating companies like it.

Confirmed intent (not superseded, not abandoned): The Company *is* the swarm. The original idea was for it to spin up additional companies to fill gaps in its own architecture - requiring the self-learning loop already partially built in Phase 11/17 (detect an inefficiency, recommend an enhancement, close the gap) to mature to the point where a detected gap can be "closed" by compiling and standing up an entirely new company, not just promoting one agent or department. Phase 17 is that same pattern at small scale (one specialist, one department); Phase 19 is its large-scale maturation. Don't schedule concrete work here until Phase 17's proposal/approval loop has enough of a real track record to trust extending it to something this consequential.

## Phase 20 and beyond — findings from the original vision comparison (2026-07-25)

Source: a direct comparison of the founder's original architecture vision against this codebase, done in this session, not derived from CrewAI or any other external framework. Method: every claim below was verified by reading the actual implementation (`workflow_engine/engine.py`, `orchestrator/head.py`, every department's `agent.yaml`, `memory_service/models.py`, `orchestrator/intake.py`, `orchestrator/classification.py`) rather than inferred from documentation or memory. None of these four phases exist anywhere in this document before this addition - they are genuinely new backlog, not a rewording of Phases 12-19.

### Phase 20 — Cost/Complexity-Aware Execution Mode

**Actual status: Implemented (2026-07-26) for model-tier selection. Parallel department dispatch deliberately deferred - see below, not the same thing as "not done."**

**Priority: Medium.**

**Deliverables**:

1. **Implemented.** `workflow_engine/complexity.py::assess_complexity()` - a real producer for `Complexity`/`Risk`/`Required Model Tier`, replacing the old fixed `"Level 2 Standard"` default (`workflow_engine/models.py`'s own docstring previously called this "no producer... exists yet"). A deliberately simple, stated heuristic (department count + Compliance involvement), not a claim to implement an undefined spec algorithm - honesty note matches `workflow_engine/review.py`'s own precedent. Immediately activated three previously-dead review tiers in `REVIEW_TIER_BY_COMPLEXITY` that only the fixed default's `"peer_review"` row could ever reach before.

2. **Implemented.** `orchestrator/execution_mode.py` - `EXECUTION_MODE` env var, `"lean"` (default) or `"fast"`, exactly parallel to `MODEL_PROVIDER`/`DEPARTMENT_CLASSIFIER`. Lean uses (1)'s assessed tier verbatim (including a real, cheaper model - `claude-haiku-4-5-20251001` - for single-department, non-Compliance objectives); Fast never downgrades below `"standard"`. A real per-call `model` override was threaded through the entire call chain to make this actually take effect, not just get computed and ignored: `ModelProvider` Protocol -> `StubModelProvider`/`AnthropicModelProvider`/`AgentSDKModelProvider` -> `ModelGateway.generate()` -> `AgentRuntime.execute_task()` -> `orchestrator/router.py::dispatch()` -> every `resolve_verdict_execution()`/`LLMDepartmentHead.evaluate()`/delegation dispatch call in `orchestrator/head.py`. The Review Agent's own dispatch is deliberately pinned to `"standard"` always, never downgraded even in Lean mode - a review gate is exactly the wrong place to spend that trade-off, per the founder's own "should not be less effective" framing.

    Also fixed in passing (same lines already being touched, not scope creep): `orchestrator/controller.py`'s Decision Record `models_used` field was hardcoded to `["stub"]` regardless of which provider was actually configured - now reflects the real model string.

3. **Deliberately deferred, not built**: running independent departments in parallel. Found during implementation, not before: `workflow_engine/engine.py::execute_workflow()`'s per-department loop shares one SQLAlchemy `Session` object across every dispatch - `Session` is not thread-safe, so naively parallelizing the loop with a thread pool (the obvious approach, and the one `Tests/integration/test_concurrent_load.py`'s HTTP-level concurrency test already used successfully at the *request* level, not the *session* level) would risk real data corruption against the dev SQLite file, not just a theoretical concern. A safe implementation needs a session-per-department-dispatch redesign, mirroring how `apps/api_gateway/queue_worker.py::run_forever()` already opens "one short-lived session per cycle" for exactly this class of problem - a bigger, separate lift than the model-tier work, and risky to rush. Not scheduled as its own phase yet; revisit if Phase 14 dogfooding reveals sequential dispatch is actually a real latency problem (Phase 13 already measured the *shared-connection* concern and found no bottleneck at the HTTP layer - this is a different, lower-level question about the workflow loop itself).

**Sequencing**: (1) shipped before (2) was wired, per this phase's own stated plan - the mode toggle had a real signal to key off before it existed.

**Why not previously tracked**: `orchestrator/classification.py` already noted "model tier selection is deferred, separate future work" - this formalizes that deferral into an actual phase instead of leaving it as an unscheduled comment.

**Test**: `Tests/unit/test_complexity.py` (department-count/Compliance thresholds, review-department exclusion, reasoning text). `Tests/unit/test_execution_mode.py` (Lean passthrough, Fast floor, env var selection/validation). `Tests/integration/test_anthropic_provider.py` and `test_agent_sdk_provider.py` (per-call `model` override wins over constructor default, falls back correctly when not given). `Tests/integration/test_coo_orchestration.py`'s new `TestPhase20ComplexityAwareModelSelection` class (end-to-end via `receive_objective()`: single-department objective actually reaches the provider as the lean-tier model, a two-department objective reaches it as standard-tier, Fast mode overrides a single-department objective to standard, the Decision Record's `models_used` reflects the real model). Two pre-existing tests updated to match real computed values instead of the old fixed placeholder (`test_knowledge_graph_review.py`'s review-tier assertions, `"peer_review"` -> `"department_review"` for a 3-substantive-department objective).

**Exit criteria**: Met for deliverables 1-2. 333 tests passing (24 new), 4 skipped (unchanged gated live-credential tests), zero unexpected regressions - the two updated tests were an anticipated, correct consequence of shipping a real computation, not a break. Deliverable 3 (parallel dispatch) has no exit criteria yet since it isn't scheduled.

### Phase 21 — Inter-Department Task Delegation

**Actual status: Implemented (2026-07-25).**

**Priority: High.**

**Deliverables**:

1. **Implemented.** A mechanism for a Department Head to request another department's help mid-task, rather than every multi-department objective being decided entirely up front by the classifier before any department starts working. `orchestrator/head.py`'s `HeadVerdict` gained `needs_department_help: str | None` (mutually exclusive with `needs_specialist` and `resolved_output` - checked in that priority order if a model response sets more than one). `resolve_verdict_execution()` routes it to a new `_resolve_department_delegation()`: the target department's own Head is evaluated (not a bare `dispatch()` - Heads are not figureheads for delegated hops either), its result is fed back to the *original* requesting Head in a second `dispatch()` call to produce a final answer incorporating it - not just relaying the sub-department's raw output. Design choice made during this phase: delegation depth is **unbounded** (the founder's explicit choice over a one-hop cap), made safe by a chain-membership check instead of a fixed limit - a department already in the current objective's delegation chain can never be re-targeted, so the worst case touches every registered department exactly once and never loops. Every successful delegation writes a `DepartmentDelegationRecord` (`orchestrator/delegations.py`), mirroring Phase 17's spawn ledger.

2. **Implemented, at the prompt level.** `LLMDepartmentHead`'s prompt now lists other departments and instructs the Head to "prefer resolving light, in-domain work... yourself - do not delegate work you can reasonably do yourself," offering `needs_department_help` only for work that is "genuinely another department's specialty." This is shared across every department via the one prompt template, not four separate `agent.yaml` edits - Phase 16's per-department boundary customization wasn't needed here since the instruction is identical regardless of department.

3. **Found to already exist - no new work needed.** Checked before building anything: `orchestrator/escalation.py`'s `EscalationCondition.NO_MATCHING_DEPARTMENT` has been one of the four canonical conditions since Phase 8, predating this session. The zero-match case was never a generic hard-reject lumped in with other failures - it's already a distinct, queryable condition on both the Decision Record and the Escalation Record. This deliverable, as scoped in the original design conversation, turned out to be a correction to this document's own vision-comparison write-up rather than real work - recorded here so the discrepancy isn't silently lost.

**Why this precedes Phase 18 in practice, if not in number**: see the sequencing note at the end of Phase 18 above - still applies; Phase 18 remains on hold pending Phase 14 signal.

**Test**: `Tests/integration/test_department_head.py`'s `TestLLMDepartmentHead` class (prompt/parsing-level: `needs_department_help` set, priority over `needs_specialist`, self-reference treated as unset, other-departments text present/absent based on whether `department_registry` was supplied). `Tests/integration/test_coo_orchestration.py`'s new `TestPhase21InterDepartmentDelegation` class (end-to-end via `receive_objective()`: successful delegation writes the ledger and finalizes through the original Head, delegation to the Review department or an unknown department falls back safely, a would-be cyclical delegation is avoided via the chain check rather than looping, direct resolution writes no delegation record).

**Exit criteria**: Met. 309 tests passing (10 new), 4 skipped (unchanged gated live-credential tests), zero changes to any pre-existing test - `department_registry`/`head`/`delegation_chain` are all optional/defaulted on every changed signature (`resolve_verdict_execution()`, `execute_workflow()`, `DepartmentHead.evaluate()`), so every pre-Phase-21 call site needed zero changes.

### Phase 22 — Artifact Pre-Assessment & Direction Confirmation

**Status: Not started. Not previously tracked.**

**Priority: Medium.**

**Deliverables**: Before routing a multi-artifact or ambiguous-scope objective, an assessment step that determines whether it should go narrow (e.g. "build this" → Engineering only) or broad (e.g. also validate Compliance requirements against supplied documents), and puts that choice back to the user explicitly rather than inferring it silently. Distinct from Phase 15's sufficiency check, which only judges "is there enough detail to act at all," not "how many departments should this touch."

**Test**: TBD at implementation time.

**Exit criteria**: TBD at implementation time.

### Phase 23 — Skill/Tool Effectiveness Memory

**Status: Not started. Not previously tracked.**

**Priority: Medium-low - no other phase depends on this; needs enough real objectives (Phase 14) to produce a meaningful effectiveness signal before it's worth building.**

**Deliverables**: Extends `memory_service`'s existing five-tier model (`MemoryTier`, already department-scoped) with a skill/agent-scoped dimension that records which tool or approach was used for a task and a measured outcome, plus a feedback path that lets future task execution prefer approaches with a better track record. Confirmed gap: today's schema has no field beyond a free-text `creator` column, and no scoring mechanism exists anywhere.

**Test**: TBD at implementation time.

**Exit criteria**: TBD at implementation time.


## Notes on scope discipline

- Phases 0–4 intentionally contain **no orchestration and no multi-agent behaviour** — they validate the substrate (identity, memory, communication, single-agent execution) in isolation, so failures in later phases can be localized instead of requiring a full-stack debug.

- The department/agent activation order (Research → Engineering+Compliance → Review) follows `FATS` §10's reasoning under MVS-canonical department naming, not `EIB`'s alternative reasoning-first ordering — both are valid; this plan picked the one that lets Phase 6 test cross-department coordination before Phase 7 adds the review gate, which is a cleaner testing progression.

- Nothing in Phases 0–9 should require touching Tier 4 (`Specifications/4 - future-expansion/`) — if an implementer finds themselves needing SDK, Plugin, Marketplace, or compiler-track content before Phase 10, that's a signal the phase boundary has been violated.

