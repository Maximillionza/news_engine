# Technology Decisions

Recorded per `Specifications/3 - execution-framework/Claude Code Bootstrap Package
(CCBP).md` sec.6. These are the concrete choices behind `IMPLEMENTATION_PLAN.md` Phase 0.

## Language

**Python 3.11+** (developed against 3.14.5). Reason: AI ecosystem maturity, agent framework
availability, data processing capability (CCBP sec.6, EIAS sec.5).

## API / service framework

**FastAPI**, with Pydantic v2 for schema validation. Reason: async support, type validation,
OpenAPI generation (CCBP sec.6, EIAS sec.6). Pydantic models are also used directly as the
RCS contract schemas (`services/shared/contracts.py`) rather than maintaining a separate
schema definition — one source of truth for both validation and typing.

## Database

**PostgreSQL** for operational data (identity, permissions, audit, tasks, workflows), per
CCBP sec.6 and `EDMS` sec.31a's storage mapping table. `docker-compose.yml` provisions a
local Postgres instance for development.

Test suites use SQLAlchemy against an in-memory SQLite database rather than requiring a live
Postgres connection - this keeps Phase 1's tests runnable without Docker while the
SQLAlchemy models remain Postgres-compatible for actual deployment. This is a test-only
substitution, not a change to the production storage decision.

## Vector store

**Dev/test:** `shared/vector_store.InMemoryVectorStore` - pure-Python, in-process,
brute-force cosine similarity. It is a storage-and-retrieval substrate only; no embedding
model is called anywhere in Phase 2, so nothing here has been validated for semantic
retrieval quality, only for correct add/search mechanics. **Production:** a real vector
database (e.g. pgvector, so it can live alongside the operational Postgres instance rather
than adding a fifth storage system) - not yet adopted, swap when retrieval quality or scale
requires it.

## Graph store

**Phase 2 decision:** no separate graph database yet. `knowledge_service` stores entities
and relationships as ordinary Postgres/SQLite tables (`knowledge_entities`,
`knowledge_relationships`) - sufficient for storage and simple lookups. A real graph
engine (Neo4j, per the original CCBP sec.6 draft decision) is deferred to Phase 7
("Knowledge Graph + Full Roster"), once workflow-generated data exists to justify
traversal-query performance work.

## Object storage

**Dev/test:** `shared/object_storage.FilesystemObjectStorage` - local filesystem, rooted
under a configurable directory, with path-traversal rejection. **Production:** S3-compatible
object storage (S3, MinIO, etc.) - not yet adopted.

## Messaging

**Dev/test:** `event_service.bus.InMemoryEventBus` - in-process, synchronous fan-out
pub/sub, with every publish routed through security_service.authorize(). **Production:**
**Redis Streams**, per CCBP sec.6 - not yet adopted; swap when cross-process or
cross-machine delivery is actually needed (nothing in Phase 3 requires it, since no service
runs out-of-process yet).

## Service-to-service request/response

`shared.service_bus.InMemoryServiceBus` - in-process request dispatch using RCS's
RequestContract/ResponseContract, with every dispatch routed through
security_service.authorize(). This has no separate CRBS-named directory (routing is treated
as shared infrastructure, like shared/db.py) and no stated production swap yet - unlike the
other Phase 0-3 substitutions, an out-of-process service mesh / API gateway routing layer
hasn't been decided because nothing outside this codebase calls it yet.

## Model provider (updated: SDK Migration Plan Phases A-C, `Documentation/plans/SDK_MIGRATION_PLAN.md`)

**Dev/test default, unchanged:** `shared/model_gateway.StubModelProvider` - deterministic, no
network access, no API key required. `ModelGateway` is still the sole holder of any
`ModelProvider` reference; `AgentRuntime` is constructed with a `ModelGateway` and has no
other way to produce agent output (see `Tests/integration/test_agent_runtime.py`'s
enforcement test).

**Real providers now exist** (`shared/providers/`), selected by the `MODEL_PROVIDER` env var
via `shared.providers.create_provider_from_env()` (`apps/api_gateway/main.py` uses this
instead of hardcoding the stub) - `stub` (default), `anthropic` (`AnthropicModelProvider`,
per-token `ANTHROPIC_API_KEY` billing), or `agent_sdk` (`AgentSDKModelProvider`, invokes
`claude_agent_sdk.query()` instead of the raw API so it can draw on a personal Claude
subscription via `CLAUDE_CODE_OAUTH_TOKEN` - see `SDK_MIGRATION_PLAN.md` Section 1 for why
that's viable here and its caveats). **The default is still `stub`, deliberately** - flipping
it in code, rather than leaving it an operator env-var choice, would mean every test run
(and every `import main`, which `Tests/integration/*.py` do repeatedly) makes real, billed
network calls. "Production" here means: the operator sets `MODEL_PROVIDER=anthropic` (or
`agent_sdk`) plus `MODEL_NAME` (optional override) when actually running the gateway for
real use, same as `THE_COMPANY_API_KEY` is already an env-var override, not a code default.

Both real providers default to **Sonnet 5** (`claude-sonnet-5`), not Opus:
`AgentRuntime.execute_task`'s Execute step is one bounded, single-shot prompt per call, not
a long agentic loop where Opus's extra depth changes the outcome - and cost is either
per-token or drawn from a personal subscription's usage window either way, so Sonnet
stretches either budget considerably further for this task shape. `MODEL_NAME` overrides it
per-deployment without a code change.

Real-API verification is real but partial: both providers have unit/integration tests
against fake clients/runners (no real network calls, matching this codebase's usual dev/test
substitution), plus a gated smoke test each (`RUN_REAL_ANTHROPIC_SMOKE_TEST=1` /
`RUN_REAL_AGENT_SDK_SMOKE_TEST=1`) that makes one real Claude call - skipped by default, and
not run as part of this work, since the environment building this had no
`ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` available. Whoever deploys this for real
should run those two smoke tests once, with their own credentials, before relying on
`MODEL_PROVIDER=anthropic`/`agent_sdk` in production.

Dynamic tier-based routing (RDL sec.8's Reasoning Tier Classification) is still not
implemented: every agent shares one `ModelGateway`/provider instance - there is no
per-department or per-agent model selection. Real routing still needs task-complexity
scoring, which per COOS sec.9's own note has no defined numeric algorithm anywhere in the
source corpus - unchanged since Phase 5's original note here.

## Agent Runtime location

`services/agent_runtime/` has no counterpart in CRBS's explicit services/ list - same
situation as `services/shared/` in Phase 0. Added because TAS Layer 3 ("Agent Execution
Layer") names Agent Runtime as a distinct architectural component and CRBS's `agents/`
directory holds agent *definitions* (data: `agent.yaml`), not the runtime *code* that
executes them.

## Objective-to-department routing

**Original Phase 5 implementation, superseded by the 2026-07-19 dynamic-department-routing
work (see "Department classification and COO sufficiency check" below):** a keyword-overlap
classifier (`orchestrator/planner.py` at the time; the exact same logic now lives, unchanged,
in `orchestrator/classification.py`'s `KeywordDepartmentClassifier`) matched an objective's
text against each department's name/purpose/mission/capabilities. This was a genuine, working
algorithm - not a stub - but weak: it found and mis-ranked a real routing dead-end during
Phase 5 testing (the empty, deliberately-out-of-MVP-scope "Strategy Department" outscored
Research on "Create a market intelligence report" purely on shared vocabulary; fixed by
excluding departments with no assigned agents from consideration, not by tuning the scorer).
A real implementation would use the Model Gateway to interpret the objective semantically
rather than matching keywords - that gap is exactly what `LLMDepartmentClassifier`
(`classification.py`, selected via `DEPARTMENT_CLASSIFIER=llm`) now fills;
`KeywordDepartmentClassifier` remains the dev/test default, same known weakness, unchanged.
Phase 6 (below) extended this same keyword matcher to multi-department routing well before
the semantic-disambiguation gap noted here was actually addressed.

## Multi-department objective routing (Phase 6)

**Phase 6 implementation, relocated (not rewritten) in the 2026-07-19 dynamic-department-
routing work:** `orchestrator/planner.py`'s `select_all_matching_departments()` extended the
Phase 5 keyword-overlap matcher (still the same weak mechanism flagged above) to return every
department scoring above zero, ordered by a fixed canonical sequence (Research, Engineering,
Compliance, Operations - this plan's own documented MVP activation order) rather than by
score, since no dependency-graph mechanism exists anywhere in the corpus to derive a real
execution order from EWOS sec.5's `Dependencies` field. This logic now lives in
`orchestrator/classification.py`'s `KeywordDepartmentClassifier.classify()` (canonical
ordering via its `_canonical_sort_key` helper), carried over unchanged rather than reworked.

**Discovery made while building this, not a Phase 6 design choice:** all four MVP
departments' `definition.yaml` files already carry a capability-aligned `agents:` entry as of
Phase 5's naming fix (`departments/engineering`, `departments/compliance`, and
`departments/operations`, not only `departments/research`). Department/agent activation in
this codebase has never been a phase-gated allowlist - it's simply "does this department's
definition.yaml list a capability-aligned agent." That means Phase 6's multi-department
matcher can already route to Compliance or Operations if an objective's vocabulary happens to
score there, ahead of those departments' documented Phase 7/8 test activation. This is not
being fixed or gated in Phase 6: the underlying agent/department definitions are already
correct and complete from Phase 5, and restricting them further would be inventing a
phase-lock mechanism nothing in the source corpus asks for. Phase 6's own test objective is
simply chosen to exercise Research + Engineering specifically.

## Risk-proportional review tier (Phase 7)

**Dev/test and current production implementation:** `workflow_engine/review.py` implements
TDL sec.17's full Routine/Standard/Advanced/Critical review-tier table, keyed by
`orchestrator/controller.py`'s `TaskProfile.complexity_level`. Since that value is still a fixed
`"Level 2 Standard"` default everywhere in this corpus (no numeric Task Complexity or Task
Risk scoring exists anywhere - TDL sec.7-8 define the scales, not how to compute a score),
`"peer_review"` is the only tier this codebase can ever actually produce right now. This is
the same honesty pattern as the department matcher and the Model Gateway's routing stub: the
table is real and consumable, the input driving it is not yet real.

Corrected while wiring this: `orchestrator/planner.py`'s fixed complexity label was
`"Level 2 Moderate"`, which doesn't match TDL sec.7's actual tier name (`"Standard"`).
Nothing consumed that string before Phase 7, so it was a latent, harmless drift until this
phase needed exact string matching against TDL's own vocabulary - fixed to
`"Level 2 Standard"`.

## Knowledge Graph wiring to workflow execution (Phase 7)

`knowledge_service` gained `get_or_create_entity` (in addition to Phase 2's `create_entity`,
which fails on a duplicate primary key) because `workflow_engine/knowledge.py` records the
same Agent and Capability entities repeatedly across separate workflow runs - a knowledge
graph accumulating relationships onto a stable entity across runs is the intended behavior,
not a collision to guard against. Each completed task (substantive or review) records
`Agent --USES--> Capability --APPLIES_TO--> Workflow`, one Capability per task (the
department's first-listed one, not every capability that task might have exercised) - TDL
sec.9's Capability Requirements model isn't implemented at per-task granularity yet, matching
the same one-task-per-department simplification already documented for `workflow_engine`.
Relationship querying remains `get_relationships_for_entity()` (by entity ID) only - no
pattern/path query engine exists yet, which is still true and still not claimed otherwise.

## Four-condition escalation policy: reachability (Phase 8)

`orchestrator/escalation.py`'s four conditions are all real, correct code paths, but two are
not reachable through `COOOrchestrator.receive_objective()`'s public entry point with this
codebase's current stub model provider and real `departments/*/definition.yaml` files:

- **OUTCOME_NOT_ACHIEVED**: `agent_runtime/runtime.py`'s Validate step (Phase 4) raises
  before ever returning an `ExecutionResult` with incomplete steps or empty output - so any
  result that reaches `evaluator.validate_outcome()` from a real `dispatch()` call already
  has `objective_achieved=True` by construction. The escalation-writing branch is still
  correct (`validate_outcome()` is a general function, not written only for this call site)
  and is tested as a direct, isolated exercise of `validate_outcome()` +
  `escalations.write_escalation()` against a hand-built `ExecutionResult`
  (`Tests/integration/test_escalation_policy.py`), not as a contrived end-to-end scenario.
- **UNRESOLVABLE_DEPENDENCY_GAP**: every real `departments/*/definition.yaml` already
  resolves to a registered agent (the Phase 5 capability-alignment fix covered all four MVP
  departments). Tested by calling `COOOrchestrator._receive_multi_department_objective()`
  directly with a deliberately-broken, in-memory `DepartmentDefinition` (not read from disk)
  referencing a nonexistent agent ID - a targeted exercise of the same escalation-wiring
  code `receive_objective()` calls, going around only the planner's department-matching step.

NO_MATCHING_DEPARTMENT, GATE_INTEGRITY_SUPERFICIAL, and TECHNICAL_FAILURE are all reachable
end-to-end and tested that way.

## Single-department routing fix: "operations" always uses the Workflow Engine (Phase 8)

Found while writing this phase's Gate Integrity Check test, not designed for it up front: a
lone department match on "operations" (the Review Agent's department) previously took
`receive_objective()`'s single-agent dispatch shortcut, which would send the raw objective
straight to the Review Agent as if it were primary work - directly contradicting
`review_agent/agent.yaml`'s own mission ("does not perform the original work it reviews").
Fixed in `orchestrator/controller.py`: any objective matching "operations," alone or with
other departments, now routes through `workflow_engine.execute_workflow()`, which already has
the review-only branch built for the multi-department case. This also happens to be exactly
the case Gate Integrity Check condition 3 needs to exercise (a review with nothing to
review) - the test uncovered a real routing gap, not the other way around.

## Compliance Intelligence Engine seeding (Phase 8)

`compliance_service/applicability.py` implements ECRIS sec.8's six-factor evaluation as a
small, explicit rule registry (ECRIS sec.9's Compliance Knowledge Model: knowledge SHALL be
stored as Rules, and explicitly SHALL NOT store generalizations). One rule is seeded - POPIA,
taken directly from ECRIS sec.8's own worked example - not a real regulatory database.
Populating one is content curation work belonging to a compliance function, not a mechanism
gap in this codebase. An unrecognized regulation returns `applicable=None` (UNKNOWN), never a
silent `False` - defaulting an unrecognized regulation to not-applicable would be a false
negative with real consequences; "we don't know, a human must review" is the honest failure
mode, the same escalate-rather-than-guess spirit as the four-condition escalation policy.

`compliance_service/policy_impact.py`'s Impact Analysis (MVS sec.12 Test Category 008) carries
its own inlined copy of the keyword-overlap matcher against department capabilities
(historically mirrored `orchestrator/planner.py`'s logic, which has since been relocated to
`orchestrator/classification.py` - `policy_impact.py`'s own copy was not touched by that
relocation), rather than inventing a second mechanism from scratch - same known weakness, not
fixed here either.

## Observability Command Centre and Alerting scope (Phase 8)

`observability_service/views.py` and `alerting.py` implement the query layer beneath EOCCS
sec.21's Command Centre and sec.25's alert ladder - no dashboard/frontend exists. Several
fields EOCCS sec.22-24 name are deliberately not populated: Director's "Long-term trends"
(needs historical time-series data not retained anywhere), COO's "Resource utilization"/
"Agent availability" (the same concurrent-task/capacity-tracking gap `orchestrator/
allocator.py` already documents for Agent Allocation), Department's "Demand"/"Knowledge
growth" (needs historical trend data). Alerting thresholds (denied -> WARNING, failed ->
HIGH_RISK, unresolved escalation -> HIGH_RISK/CRITICAL) are illustrative defaults, not tuned
from real operational data - same honesty as every other fixed-default decision in this
corpus.

## Trust scoring and incident response scope (Phase 8)

`security_service/trust.py` computes only ESTAS sec.26's "Error rate" factor (denied-decision
ratio from the actor's own audit trail) - Compliance performance, Security behaviour, and
Validation results all need machinery not built anywhere in this corpus (compliance
assessments tied to a specific actor; Prompt Injection Defence / Agent Behaviour Monitoring,
ESTAS sec.22-23). The computed trust level is persisted onto `Identity.trust_level`; ESTAS
sec.26's last paragraph ("Trust scores SHALL influence Permissions, Review requirements,
Resource allocation") is not wired into enforcement in this pass - that's a genuine
permission/authorization-logic change with a wider blast radius than this phase's exit
criteria calls for, tracked here rather than silently dropped.

`security_service/incidents.py` implements ESTAS sec.28's seven-stage Incident Workflow as a
forward-only state machine - no skip, no loop back, a deliberate simplification (real
incident handling sometimes needs to revisit an earlier stage). Incidents are opened
explicitly by whatever detects a security-relevant event; this module is intentionally not
wired into `orchestrator/escalation.py`'s four-condition policy - that policy concerns
workflow/task governance verdicts, this concerns security events, and ESTAS itself treats
these as distinct concerns (sec.26's own Trust/Authority/Autonomy separation draws the same
kind of line).

## Tiered Learn step: criticality signal and reachability (Phase 9)

`orchestrator/controller.py._learn()` uses Phase 8's Escalation Records as the sole
criticality signal: a workflow with zero Escalation Records for its decision_id is "minor"
(self-approved straight to Historical tier); one or more makes it "critical" (held at
Project tier via `memory_service/promotion.py`'s `LessonPromotion`, pending human
`approve_promotion()`/`reject_promotion()`). No second risk classification was invented -
this was an explicit user decision (see the Idea Lab design-decision entry above).

`_learn()` and `router.py`'s new department-observation write are both **best-effort**: each
requires the acting identity (`coo`, or the executing agent) to hold an explicit
`memory:<tier> write` grant, per the no-bypass invariant `memory_service/repository.py` has
enforced since Phase 2. Most pre-Phase-9 test fixtures only grant `memory:department read`
to agents (nothing wrote before this phase) and never grant the `coo` identity any memory
permission at all - by design, not oversight, so those fixtures don't need updating. Both
call sites catch `PermissionError`, write an audit record, and continue; a missing memory
grant must never retroactively undo an objective that already completed successfully.
Fixtures that want the Phase 9 behaviour (Tests/acceptance/test_mvs_acceptance.py,
Tests/integration/test_lesson_promotion.py) grant `memory:department write` to agents and
`memory:historical write` / `memory:project write` to `coo` explicitly.

## "Performance improves" (MVS sec.9 Test Category 005): honest definition

This codebase has no real model (`StubModelProvider` is deterministic and content-blind) and
no quality-scoring mechanism anywhere in the corpus, so "the second execution improves"
cannot mean "produces better output." What Phase 9 built instead (the department-observation
write in `orchestrator/router.py`) makes a real, structural claim true: the pool of
Department-tier memory available to `agent_runtime/runtime.py`'s Retrieve Relevant Knowledge
step (Step 3, built in Phase 4, never fed by anything until now) strictly grows after each
completed task. `Tests/acceptance/test_mvs_acceptance.py`'s MVS-005 test asserts that growth
directly - not a fabricated quality delta.

## Model Gateway hot-swap (Phase 9, MVS sec.14 Test Category 010)

`shared/model_gateway.py`'s `ModelGateway.replace_provider()` lets a caller swap the
underlying `ModelProvider` without any consumer (`AgentRuntime`, `workflow_engine`, ...)
changing - the same "swap without touching callers" principle the module already stated for
the dev/test-to-production substitution. This is a manually-triggered hot-swap, not an
automated detect-and-recover daemon: EOCCS sec.20's full "Automated Intervention" loop
(Detection -> ... -> Recovery, wired end-to-end without a human deciding to call this) is not
built. `Tests/acceptance/test_mvs_acceptance.py`'s MVS-010 test triggers it explicitly after
observing a TECHNICAL_FAILURE escalation and a CRITICAL alert.

## SDK scope: what "no core runtime code changes" actually meant (Phase 10)

`sdk/agent_builder/builder.py` is the only SDK component IMPLEMENTATION_PLAN.md's Phase 10
test requires ("register in the Agent Registry and execute a task successfully through the
existing COO/workflow path"). It reuses `AgentDefinition`, `AgentRegistry`, `AgentRuntime`,
`DepartmentRegistry`, `identity_service`, and `security_service` exactly as Phases 1-4 built
them - the only new code is the orchestration of those existing pieces plus ESDKS sec.7's
Validation Pipeline shape (`sdk/validation/pipeline.py`). "Executes a task successfully
through the existing COO/workflow path" is interpreted as `orchestrator/router.py`'s
`dispatch()` - the one function both `controller.py`'s single-department path and
`workflow_engine.execute_workflow()`'s per-task loop call for every task since Phase 5 - not
a full `receive_objective()` run, since that would require also editing a department's
`agents:` list in `departments/*/definition.yaml` (a data-file edit, not a runtime-code
edit, but not required to prove the exit criterion either) so the keyword matcher could ever
select the new agent over the department's existing one. See
`Tests/integration/test_sdk_agent_builder.py`'s module docstring.

ESDKS sec.16's own MVP SDK Requirements list (Agent generator, Schema validation, Capability
definitions, Workflow templates, Tool interface, Testing integration) does not include the
Department Builder (sec.5.2) - it was skipped entirely for this reason, not an oversight.
`sdk/capability_builder/` and `sdk/workflow_builder/` produce validated `Capability`/
`WorkflowTemplate` objects (Schema Validation only - see their own module docstrings for why
Security Review/Capability Test/Architecture Check don't apply to definitions with no
runtime) but are **not** wired into anything else in this codebase yet: department/agent
capability matching (`orchestrator/classification.py`, `allocator.py`) still compares plain
strings, and `workflow_engine.execute_workflow()` still derives its task list from
department keyword-matching, not from a stored `WorkflowTemplate`. Both are named gaps, not
silently dropped - closing them is real, separate follow-up work. "Tool interface" (ESDKS
sec.5.5) was folded into `plugin_service`'s Tool Plugin type (EPAS sec.5.1) rather than
building a second, parallel tool schema - the two specs describe the same underlying
mechanism (an agent gaining access to an external capability), so one schema serves both.

## Plugin/Marketplace validation: which gates are real (Phase 10)

`plugin_service.registry.validate_plugin()` and `marketplace_service.registry.validate_asset()`
both implement only the validation dimensions this codebase can actually check without a
live runtime to execute the packaged component against: Schema Check/Architecture Validation
(required fields present, enum values valid) and a minimal Security Review/Validation
(security classification recognised; access genuinely permission-gated). EPAS sec.8's
Capability Test + Integration Test and EMAS sec.9's Technical Validation + Performance
Validation are named in both modules' docstrings as not implemented - they would require
executing an arbitrary packaged plugin/asset and measuring the result, and no plugin/asset
runtime exists anywhere in this corpus to do that against. This mirrors the exact honesty
pattern already established for workflow_engine's Gate Integrity Check (Phase 8) and the
Model Gateway's routing stub (Phase 4): the pipeline shape is real, the parts of it that need
data or infrastructure this codebase doesn't have are named, not faked.

## API Gateway: dev-mode bootstrap and auth (Phase 10)

`apps/api_gateway/main.py` now constructs a real `COOOrchestrator` at import time, backed by
a SQLite file (`api_gateway_dev.sqlite3`, gitignored) rather than in-memory SQLite - an
in-memory SQLite connection is scoped per-connection, so identities/permissions granted at
startup would vanish between requests without a file (or a shared-cache/StaticPool
configuration this module doesn't use). Every already-scaffolded agent (and `coo` itself) is
granted the same permissions every Phase 5-9 test fixture sets up by hand, so a fresh
deployment works without manual setup. Authentication is a single static `X-API-Key` header
check (`THE_COMPANY_API_KEY` env var, defaulting to a dev-only value) - EAAS sec.18 requires
"Authentication" exist at MVP level, it does not mandate OAuth/JWT/sessions; this is
explicitly a placeholder, swap when a real identity provider is wired in.

## Evolution Engine: real inefficiency, real simulation, honest "implementation" (Phase 11)

`evolution_service/detection.py` deliberately reuses `orchestrator/escalation.py`'s
GATE_INTEGRITY_SUPERFICIAL condition (Phase 8) as its one detected inefficiency, rather than
inventing a second detection mechanism or a synthetic "deliberately inefficient workflow"
solely for Phase 11's test. The "operations only" objective already used since Phase 8 to
exercise the Gate Integrity Check (`Tests/integration/test_escalation_policy.py`,
`test_lesson_promotion.py`) is exactly MVS-011's "deliberately inefficient workflow" - a
review step that runs with nothing to review. This is intentional reuse, not coincidence:
every real signal this codebase produces is a legitimate Evolution input, and inventing a
parallel, unrelated "inefficiency" would have meant building a second detector nobody else
uses, purely to satisfy one phase's test.

`simulation_service.workflow_simulation.simulate_workflow_change()` runs both the baseline
and proposed department lists through the real, unmodified `workflow_engine.execute_workflow()`
- each in its own throwaway in-memory database and freshly-granted identity set, never the
caller's real session. This is ESDTS sec.9's Environment Separation taken literally: a
simulation cannot write production state because it never touches the production session at
all, not because of a policy that trusts callers to be careful. `confidence` is fixed at 0.4
and the reason is spelled out in `limitations` - no real model or business-outcome measure
exists anywhere in this corpus (the same honesty `orchestrator/planner.py` originally
established for its complexity default, now carried forward in `orchestrator/controller.py`'s
`TaskProfile`, and `workflow_engine/review.py`'s tier mapping), so "predicted_results" means
"observed dry-run metrics," never a forecast.

`evolution_service.pipeline.EvolutionEngine.implement_change()` writes an EESIS sec.14
Evolution Memory record (reusing `memory_service.write_memory()`, Phase 9's infrastructure)
and marks the proposal IMPLEMENTED - it does **not** automatically change what
`workflow_engine.execute_workflow()` does for a future "operations only" objective. This was
a deliberate scope decision, not an oversight: wiring an approved Evolution proposal to
actually mutate `workflow_engine`'s tested, load-bearing runtime behaviour would require
threading a new flag-lookup through `orchestrator/controller.py` and `workflow_engine/
engine.py`, both already exercised by dozens of passing tests across seven earlier phases -
the risk of destabilizing that path outweighed the value of a fully-automatic closed loop for
this one demonstrated inefficiency. It also mirrors Phase 9's own precedent exactly: an
approved lesson promotion (`memory_service/promotion.py`) writes a new memory object: it does
not automatically change any agent's behaviour either. Wiring approved Evolution changes into
live runtime behaviour is real, named, separate follow-up work.

The Evolution Engine's own identity (`engine_identity_id`, default `"evolution_engine"`) is
never granted the `evolution:change_proposal approve` permission by anything in this
codebase. `approve_change()`/`reject_change()`/`implement_change()` all route through the
same `security_service.authorize()` no-bypass chain every other privileged action in this
corpus uses - the "Evolution Engine cannot self-approve changes" requirement (EESIS sec.10,
ESTAS sec.21) is enforced structurally by the absence of a grant, not by a special-cased
`if identity == engine_id: deny` check that could be forgotten in a future call site.

## Orchestrator directory structure

CRBS's original scaffolding gave `services/orchestrator/` five empty subdirectories
(`planner/`, `allocator/`, `router/`, `evaluator/`, `controller/`). These were removed in
Phase 5 and replaced with flat modules of the same names, for consistency with every other
service in the codebase (none of which use subdirectory packages). No content was lost -
the subdirectories only ever contained unmodified placeholder READMEs.

## Containerisation

**Docker Compose** for local development (`docker-compose.yml`, currently provisioning
Postgres only; services are added as they're built). **Kubernetes** is the stated future
target for production per CCBP sec.6, not adopted yet.

## Testing

**pytest**, with `pytest-cov` for coverage and `httpx`/FastAPI's `TestClient` for API tests.

## Escalation policy and lesson-promotion (Phase 8/9 design, adopted ahead of build)

Source: a separate swarm project ("Idea Lab," a Claude Code subagent-orchestration build,
not part of this repository) was reviewed for repurposable patterns. Two were adopted by
explicit user decision; everything else reviewed was declined. Both are recorded here now,
ahead of Phase 6/7, so the design is fixed before Phase 8/9 implementation begins — not
because either is being built yet.

**Four-condition escalation policy** (Phase 8 deliverable, see `IMPLEMENTATION_PLAN.md`).
Adopted in place of inventing a numeric risk/complexity score for ESTAS §10, since COOS §9
has no such algorithm anywhere in the source corpus (confirmed during the Specifications/
reconciliation, re-confirmed in the module's docstring at the time - since relocated to
`orchestrator/classification.py`). Idea Lab escalates to
its human user for exactly four named framework-verdict conditions plus technical failures,
logged separately; The Company's four conditions are COOS-equivalents of those, not a literal
port (no viable department match, outcome validation failure, a review gate flagging a
nominally-passing result as superficial, an unresolvable cross-department dependency gap).
This is a small, explicit, named-condition list, not a scoring model — deliberately, since a
short list is auditable and a numeric score the corpus never defined would not be.

**Tiered Learn-step promotion** (Phase 9 deliverable). Idea Lab gates every playbook lesson
behind human approval, with no exceptions. The user's explicit instruction for The Company was
narrower than a flat port: split by criticality rather than applying one uniform gate.
- Minor/incremental lesson (workflow completed without tripping any Phase 8 escalation
  condition): the COO self-approves and writes directly to the Historical tier as a new,
  self-contained memory object.
- Critical lesson (a Phase 8 escalation condition fired, or a technical failure occurred):
  held pending human approval; the COO continues normal operation on other objectives while
  the decision is outstanding (async, non-blocking approval).
- Explicit fallback: if this split proves to add complexity, errors, or project-specific bias
  to Historical-tier memory, revert to human-approval-only for all promotions, minor or
  critical, and only reintroduce auto-approval of minor lessons once there is a track record
  showing it doesn't regress alignment/complexity/bias. This fallback is not optional or a
  last resort — treat it as the default correction whenever Phase 9 testing raises doubt.

Deliberately declined from the same review: Idea Lab's deterministic case-type routing table
(doesn't transfer — The Company's objectives are open-ended text, not a closed case-type set;
the existing keyword-overlap weakness noted below is still the right thing to revisit in
Phase 6), the Vendor-vs-Panel ad hoc dispatch distinction, and treating
`StructuralEnhancements.md`-style deferred-log formatting as its own artifact (The Company's
existing discipline of docstring notes + this file already serves that purpose).

## Project layout

Standard Python package layout was intentionally *not* imposed on top of CRBS's repository
structure. Services live at `services/<service_name>/` and apps at `apps/<app_name>/` exactly
as CRBS defines; `pyproject.toml`'s `pythonpath` is set to `services/` so cross-service
imports (e.g. `from shared.contracts import RequestContract`) work without a `src/` layer
CRBS never specified.

## Department classification and COO sufficiency check (2026-07-19 design doc)

`orchestrator/planner.py`'s keyword-overlap department matcher is gone - relocated behind a
swappable `DepartmentClassifier` interface (`orchestrator/classification.py`), exactly
parallel to `shared/model_gateway.py`'s `ModelProvider` pattern. `KeywordDepartmentClassifier`
(the exact old logic, unchanged) is still the dev/test default; `LLMDepartmentClassifier`
(real Claude-backed routing) is selected via `DEPARTMENT_CLASSIFIER=llm`, mirroring
`MODEL_PROVIDER`. `COOOrchestrator.receive_objective()` now makes exactly one classification
call per objective (previously two redundant keyword-matching calls - harmless when free,
wasteful once real). The Decision Record's `reasoning` string also changed shape as part of
this relocation - from `"Matched department 'X' with keyword-overlap score N..."` to
`"Matched N department(s) via keyword overlap: [...]"` - a non-breaking, informational change
only, since nothing in this codebase parses that string.

`orchestrator/intake.py`'s `assess_sufficiency()` adds a COO-level check, chat-only (`POST
/objectives` and `POST /chat/sync` don't use it): round 1 asks a normal clarifying question if
detail is lacking; round 2 reframes as an explicit "proceed as-is or give more detail" choice;
round 3 is a hard cap enforced in code (no model call), guaranteeing the loop terminates.
`DashboardChatMessage.is_clarifying_question` (new column) is how `dashboard_api.py` counts
which round it's in.

Both new model calls reuse whatever `ModelGateway`/provider is already configured (Sonnet 5 by
default per `SDK_MIGRATION_PLAN.md` Phase C) - no new tiering axis. Real model tier selection,
Department Head triage, dynamic agent selection, and token budget management remain
deliberately out of scope - see `2026-07-19-dynamic-department-routing-design.md` Section 6.
