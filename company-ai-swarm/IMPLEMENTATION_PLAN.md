# The Company — Milestone-Based Implementation Plan

Version 1.0, synthesizing the build sequences already defined across `Specifications/2 - construction-framework/Enterprise Implementation Blueprint (EIB).md`, `Specifications/3 - execution-framework/AI Builder Master Execution Package (ABMEP).md`, and `Specifications/3 - execution-framework/MVP Validation Specification (MVS).md` into one concrete, testable sequence.

**Status note (reconciled 2026-07-23, PRD `Documentation/plans/2026-07-23-closing-the- crewai-capability-gap-prd.md` initiative 5.1):** this document previously stated "No code has been written against this plan — it is a planning artifact only." That was false and had drifted badly out of date. As of this reconciliation, all twelve phases have real, substantially-implemented code and passing tests - see the status table below. This reconciliation is a repo-state check (do the files and tests described by each phase's deliverables exist and pass), not a line-by-line re-audit of every exit-criteria bullet - treat "Implemented" below as strong evidence, not a formal phase sign-off.

## How to read this document

Twelve phases. Each phase has:

- **Depends on** — which prior phases must be *done* (not just started) before this one can begin.

- **Deliverables** — what gets built, named against the repository structure already scaffolded (`agents/`, `services/`, `departments/`, etc.).

- **Test** — how this phase is validated **on its own**, without needing any later phase to exist. This is the hard requirement: if a phase's test can only pass once a future phase is also built, the phase boundary is wrong and should be redrawn.

- **Exit criteria** — the observable state that means "this phase is done."

Phases 0–9 constitute the MVS-canonical MVP (Director + COO + Research/Engineering/ Compliance/Operations departments + one agent each + full governance layer). Phases 10–11 are explicitly post-MVP, per EIB Phase 3/4 and CCBP §10 ("First Expansion After MVP"). Phases 12 onward (added 2026-07-23, see "Phase 12 and beyond" below) are this document's single source of truth for what's built vs. what's next, superseding the standalone `Documentation/plans/2026-07-23-closing-the-crewai-capability-gap-prd.md` for status tracking — that document's reasoning/evidence stays valid, its initiatives now live here as numbered phases instead, so status isn't tracked in two places.

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
```

No phase may begin before its predecessor's exit criteria are met. This mirrors the Build Dependencies chain in EIB §12 (Identity → Security → Runtime → Agents → Workflows → Departments → Expansion Systems).

## Actual status (reconciled 2026-07-23)

Full test suite: **266 passed, 4 skipped** (`python -m pytest`). The 4 skipped are all gated live-credential smoke tests (real Claude API/Agent SDK calls, opt-in via env var), not failures or missing coverage. The MVS acceptance suite (`Tests/acceptance/ test\_mvs\_acceptance.py`) covers all 10 of Phase 9's categories in one file (13 test methods) and passes in full - this is Phase 9's own exit criteria, met.

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
| 12 | Agent Tool-Calling | Not started | Priority: **High**. See "Phase 12 and beyond" below. |
| 13 | Failure & Load Resilience Testing | Not started | Priority: **High**. |
| 14 | Operational Dogfooding | Not started | Priority: **Medium**, ongoing once started (no end date). Depends on Phase 12. |
| 15 | Intake Sufficiency-Check Coverage Extension | Implemented (2026-07-23) | `apps/api_gateway/dashboard_api.py::chat_send_sync` now runs the same sufficiency gate as `chat_send`; `apps/api_gateway/main.py::submit_objective` runs a single-shot (no round-loop) version, since `/objectives` has no conversation state to count rounds against. 272 tests passing, 4 skipped (same gated live-credential tests as before), including 5 new tests covering the insufficient/third-round/rejection paths on both endpoints. |
| 16 | Department Head Direct Execution + Specialist Spawning | Implemented (2026-07-23) | `orchestrator/head.py::resolve_verdict_execution()` (shared mechanism), wired into both `controller.py` (single-department) and `workflow_engine.py` (multi-department); `LLMDepartmentHead` now attempts objectives directly. All four head agent.yaml files updated. 282 tests passing, 4 skipped, zero changes to any pre-existing test (full backward compatibility confirmed). |
| 17 | Specialist Spawn Ledger + Evolution Promotion Heuristic | Not started | Priority: **Medium**. Depends on Phase 16. |
| — | Department Creation Capability | Deferred | No phase/priority assigned yet —Priority: **Low, deliberately deferred** until Phase 14 produces real case data. |
| — | Enterprise Compiler / CEDL (multi-company generation) | Long-horizon | No phase/priority assigned yet —Not scoped. Depends on Phase 17's small-scale self-improvement loop earning a track record first. |
| — | EEOS (Economics & Optimization) | Needs exploration | No phase/priority assigned yet — scope this before scheduling it. |
| — | EDIS (Deployment & Infrastructure) | Not a gap | `Infrastructure/`'s empty scaffolding is correct as-is — purpose-built to stay empty until the Company has real operational/project history (Phase 14). Revisit then, not before. |
| — | EHCAS §13 "Decision Authority Class" | Resolved | Superseded by Phase 8's escalation policy (`orchestrator/escalation.py::EscalationCondition`) — no separate work needed. |


Full detail for Phases 12-19 (deliverables, test approach, open questions) is in "Phase 12 and beyond" below, in the same format as Phases 0-11 above.


## Phase 0 — Foundation & Contracts

**Depends on**: nothing (repository structure and configuration templates already exist — see `CRBS`, `agents/templates/agent\_template.yaml`, `Configuration/company.yaml`).

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

  4. A downstream department/agent in a multi-department workflow (Phase 6/7 Workflow Engine) hits a dependency or traceability gap it cannot resolve within its own capability/context. A technical failure (agent runtime exception, Model Gateway failure, output that fails RCS contract validation) always escalates too, but is logged as a technical failure, distinct from the four framework verdicts above — never conflate the two in the Decision Record.

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

- they came out of a direct architecture review against CrewAI and a codebase-grounded discussion of self-organization concepts, both on 2026-07-23. Same format as above (Depends on / Deliverables / Test / Exit criteria) where the work is scoped enough to support it; phases still needing scoping say so plainly instead of inventing false precision.

### Phase 12 — Agent Tool-Calling

**Depends on**: Phase 4 (Agent Runtime), Phase 10 (SDK).

**Priority: High.**

**Deliverables**: `AgentSDKModelProvider`'s `allowed\_tools` mechanism already exists and is wired into the Claude Agent SDK's own tool loop - it has simply never been populated. Wire one real tool per department, matched to its actual mission: Research gets a web-search tool, Engineering gets a sandboxed code-execution/lint/test-runner tool, Compliance gets a policy/document-lookup tool. Do not build a general-purpose tool library up front - that's explicitly out of scope (see the CrewAI-gap PRD's non-goals).

**Test**: At least one department agent completes a real objective requiring an external tool call mid-reasoning, with that call visible in `observability\_service/telemetry.py` - not just inferable from the final text output.

**Exit criteria**: One department agent demonstrably uses its tool in a real (non-test) objective, logged in telemetry.

### Phase 13 — Failure & Load Resilience Testing

**Depends on**: Phase 9 (objective queue, escalation policy).

**Priority: High.**

**Deliverables**: `Documentation/plans/SDK\_MIGRATION\_PLAN.md` Section 1 already flags shared subscription-usage-window contention as a real risk; nothing tests it. Three targeted tests, not full Phase 11 simulation scope: (1) N concurrent objectives through `queue\_worker.py` - no queue corruption, no lost/duplicated jobs; (2) a forced provider failure mid-workflow - confirms the technical-failure escalation path Phase 8 already defines fires correctly and is distinct from the four framework-verdict conditions; (3) one soak test over an extended run, confirming no resource leak or worker deadlock.

**Test**: Automated, committed tests for (1) and (2) at minimum; (3) documented even if run manually.

**Exit criteria**: Both (1) and (2) pass as committed tests.

### Phase 14 — Operational Dogfooding

**Depends on**: Phase 12 (enough real tool capability to make it worth running).

**Priority: Medium — ongoing once started, no end date, runs in parallel with later phases.**

**Deliverables**: A passing test suite proves the system handles scenarios its author anticipated; it doesn't prove what CrewAI's independent user base proves for free. Route a defined set of real (non-test) objectives through the swarm over time. Review every Decision Record produced - not just success/failure, but whether department routing, escalation, and memory promotion were actually correct. Convert every mistake found into a new regression test.

**Test**: N/A - this phase generates test cases, it doesn't consume a pre-written one.

**Exit criteria**: A running log of real objectives processed, each with its Decision Record reviewed, and at least one regression test added per incorrect behavior found. Also the data source for Phase 18's deferred department-creation work and for scoping real infrastructure needs (EDIS, currently correctly unscheduled - see the status table above).

### Phase 15 — Intake Sufficiency-Check Coverage Extension

**Depends on**: Phase 5 (COO). Builds on the existing `orchestrator/intake.py`.

**Priority: High — foundational. Phase 16's Head-spawning conditions depend on this holding** **across every entry point, not just one.**

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

**Deliverables**: `intake.py::assess\_sufficiency()` already does exactly this - checks whether an objective has enough detail before dispatch, and asks a bounded clarifying question if not (capped at 3 rounds). Its own docstring is explicit that it's wired to only one of three entry points: `POST /chat` (the dashboard). `POST /chat/sync` (what Samaritan's `dispatch\_to\_company()` actually calls) and `POST /objectives` (the formal API) skip it entirely. Extend the same sufficiency gate to both. Samaritan itself should not need to reason about objective completeness - per its own design, it's meant to leverage the swarm, not duplicate its judgment - so this belongs entirely on the swarm side.

**Test**: Submit a deliberately under-specified objective via `/chat/sync` and via `/objectives`; confirm each surfaces a clarifying-question path equivalent to what `/chat` already does today, rather than dispatching on incomplete information.

**Exit criteria**: All three entry points enforce the same completeness gate before an objective ever reaches a department.

### Phase 16 — Department Head Direct Execution + Specialist Spawning

**Depends on**: Phase 15 (the completeness gate must hold everywhere first - see below for why).

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

**Deliverables**: Today, `orchestrator/head.py`'s `DepartmentHead.evaluate()` is a pure accept/reject gate - it never executes work itself. Reframe it: a Head attempts execution directly, and spawns an additional (specialist) agent only when one of two explicit conditions holds:

1. The information/context provided does not give the Head enough to confidently judge whether more headcount is required.

2. The Head's own analysis of the work - however complete that analysis is - still falls short of what one agent can deliver.

Condition 1 is deliberately narrow, not a routine escape valve: insufficient information is an *intake defect* to fix upstream (Phase 15), not something a Head should be expected to absorb by guessing. This is a design principle, not just an implementation detail - it needs to be written down somewhere departments/agents can be held to it (a DOMS-adjacent documentation update, not only code), so "the Head didn't have enough to go on" stops being an acceptable justification for spawning once Phase 15 is in place.

This changes the `HeadVerdict` contract - today `\{accepted, reasoning, suggested\_department\_id\}` - to something that can carry either a direct result or a delegation, e.g. `\{resolved\_by: "head"|"specialist", output, escalation\_reason\}`. That ripples into the Decision Record schema and Phase 8's escalation classification: a Head that genuinely can't finish isn't the same event as the four existing conditions - it's arguably a fifth, not a variant of an existing one.

**Test**: Not yet fully specified - needs definition once the contract change above is implemented. At minimum: an objective sized for one agent completes via the Head alone with no spawn; an objective genuinely exceeding one agent's capacity triggers a spawn with a recorded reason matching condition 1 or 2 above, never neither.

**Exit criteria**: TBD at implementation time.

### Phase 17 — Specialist Spawn Ledger + Evolution Promotion Heuristic

**Depends on**: Phase 16 (spawning has to exist before its pattern can be tracked).

**Priority: Medium.**

**Deliverables**: A historical record of every specialist spawned by a Department Head (Phase 16), tagged by specialization. A new Evolution Engine detection heuristic reading that ledger for a repeated need for the same specialization - note this is a genuinely different shape from `evolution\_service/detection.py`'s existing `detect\_inefficiencies()`, which is scoped to one decision at a time; this needs a periodic or cross-decision pass, not an inline per-decision check like today's only heuristic. Two new `ChangeProposal` types: create a dedicated agent (wired to `sdk/agent\_builder`'s already-working `build\_agent()` - schema-validates, creates identity, grants permissions, runs a real smoke-test execution, registers into the live `AgentRegistry`, no restart needed) and create a new department (needs Phase 18, since no equivalent builder exists yet). Also worth knowing going in: `evolution\_service/pipeline.py::implement\_change()` currently only ever writes a memory record saying a change was "approved and implemented" - it does not mutate any runtime behavior for any existing proposal type. Wiring "create agent" to actually call `build\_agent()` on approval is the first case of this pipeline doing real work, not an incremental addition to a pattern that already does.

**Test**: TBD at implementation time.

**Exit criteria**: TBD at implementation time.

### Phase 18 — Department Creation Capability

**Status: Deliberately deferred.**

**Priority: Low.**

**Deliverables**: An `sdk/department\_builder`, parallel to `agent\_builder`'s `build\_agent()`

- activating `orchestrator/department\_registry.py`'s `DepartmentDefinition.lifecycle\_state` field, which already defaults to `"proposed"` but is never read or enforced anywhere today.

**Why deferred**: not a technical blocker - a deliberate choice. The Company needs to process real cases first (Phase 14) before there's tangible information about which new department(s), if any, are actually necessary. Building this speculatively risks the same "a lot of surface area for one operator" problem already flagged in the CrewAI comparison. Revisit once Phase 14 has produced real signal, not before.

### Phase 19 — Enterprise Compiler / CEDL (long-horizon)

**Depends on**: Phase 17 (the small-scale version of this same pattern needs a track record first).

**Status: Not scoped. Long-horizon.**

Source: `Specifications/4 - future-expansion/`'s Volumes XXXII (MCDP), XXXIII (EMMS), XXXIV (CEDLS), XXXVII (EBAS), and XXXVIII (ERAS) - no code exists against any of them today. These describe something categorically bigger than everything else in this document: a declarative language (CEDL) for defining an AI-native enterprise as data, compiled and provisioned by a generic Enterprise Compiler/Builder/Runtime - not a feature of this Company, but a platform for generating companies like it.

Confirmed intent (not superseded, not abandoned): The Company *is* the swarm. The original idea was for it to spin up additional companies to fill gaps in its own architecture - requiring the self-learning loop already partially built in Phase 11/17 (detect an inefficiency, recommend an enhancement, close the gap) to mature to the point where a detected gap can be "closed" by compiling and standing up an entirely new company, not just promoting one agent or department. Phase 17 is that same pattern at small scale (one specialist, one department); Phase 19 is its large-scale maturation. Don't schedule concrete work here until Phase 17's proposal/approval loop has enough of a real track record to trust extending it to something this consequential.


## Notes on scope discipline

- Phases 0–4 intentionally contain **no orchestration and no multi-agent behaviour** — they validate the substrate (identity, memory, communication, single-agent execution) in isolation, so failures in later phases can be localized instead of requiring a full-stack debug.

- The department/agent activation order (Research → Engineering+Compliance → Review) follows `FATS` §10's reasoning under MVS-canonical department naming, not `EIB`'s alternative reasoning-first ordering — both are valid; this plan picked the one that lets Phase 6 test cross-department coordination before Phase 7 adds the review gate, which is a cleaner testing progression.

- Nothing in Phases 0–9 should require touching Tier 4 (`Specifications/4 - future-expansion/`) — if an implementer finds themselves needing SDK, Plugin, Marketplace, or compiler-track content before Phase 10, that's a signal the phase boundary has been violated.

