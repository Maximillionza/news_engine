# Design: COO Intent Understanding & Sufficiency Check (Phase 1 of Dynamic Model Selection)

**Status:** Approved design, not yet implemented.
**Date:** 2026-07-19
**Relationship to Documentation/plans/SDK_MIGRATION_PLAN.md:** independent of that plan. This
originated from a request to make the swarm's model selection dynamic (COO picks a starting
model/tier, Department Head can adjust it with subject-matter reasoning) rather than the
hardcoded per-provider defaults SDK_MIGRATION_PLAN.md Phase C shipped. That request turned out
to describe five separable capabilities:

1. COO intent understanding + sufficiency check (**this spec**)
2. Department Head triage (accept / reassign / decline-as-not-worth-the-swarm)
3. Dynamic agent count & selection within a department
4. Specialist agent creation on demand
5. Token/cost budget management as a first-class input
6. Model tier selection itself (the smallest, most downstream piece - depends on 1-5 actually
   working)

Items 2-6 are each substantial sub-projects and are explicitly **out of scope** for this spec.
This document covers only item 1.

---

## 1. Problem Statement

**Current state** (`services/orchestrator/planner.py`):
- Department routing is a keyword-overlap classifier: tokenize the objective, tokenize each
  department's name/purpose/mission/capabilities, pick department(s) whose token sets
  intersect. The module's own docstring already calls this "weak" and states a real
  implementation would use the Model Gateway semantically - this has always been a documented
  stand-in, not a hidden gap.
- There is no sufficiency check at all. Whatever detail-level a user provides in one chat
  message is what gets routed and executed - a vague or under-specified request either
  mis-routes, executes against wrong assumptions, or trips `NoMatchingDepartmentError` if
  literally no keyword overlaps.
- `POST /chat` (`apps/api_gateway/dashboard_api.py`) is fire-and-forget as of
  SDK_MIGRATION_PLAN.md Phase B: it enqueues and returns `{objective_id, status}` immediately;
  a background queue worker (a separate OS process, see `Scripts/run_queue_worker.py`) later
  calls `COOOrchestrator.receive_objective()` and writes the reply back into the chat
  transcript.

**Why this matters:** the user's real-world objectives span wildly different domains (app
development, Forex trading strategy design, website design, business case formation) at
wildly different levels of initial detail. Keyword matching cannot tell "deep research is
implicitly required here even though the word 'research' never appears" from "this genuinely
doesn't belong to any department." And nothing today asks the user for more detail when a
request is too vague to act on - it just does its best with whatever keywords happen to
overlap.

---

## 2. Scope of This Spec

**In scope:**
- A sufficiency check: before an objective is ever enqueued, the COO judges whether there's
  enough detail to act on it, and if not, asks the user a clarifying question (via the
  existing chat transcript) - with a bounded number of rounds, not an indefinite loop.
- Replacing `planner.py`'s keyword-overlap department matching with real, context-aware
  reasoning - but keeping the keyword matcher as the swappable **dev/test default**, exactly
  parallel to how `StubModelProvider` is the dev/test default `ModelProvider`.

**Out of scope (future sub-projects, not designed here):**
- Department Head triage/reassignment/decline judgment.
- Dynamic agent count or specialist agent creation.
- Token/cost budget management as a decision input.
- Model tier selection (which model actually executes the task). This spec's new model calls
  (sufficiency check, classification) reuse whatever `ModelGateway`/provider is already
  configured (per SDK_MIGRATION_PLAN.md Phase A-C, defaulting to Sonnet 5) - no new tiering
  axis is introduced here.
- `POST /chat/sync` is unchanged - it keeps calling `receive_objective()` directly with no
  sufficiency check, preserving its role as the deterministic, fully-synchronous path for
  tests/callers that don't want the new conversational behavior.
- `POST /objectives` (the EAAS-spec synchronous endpoint) gets the classifier replacement
  (since it lives inside `receive_objective()`) but **not** the sufficiency check, which is
  chat-specific pre-flight logic. Programmatic callers are assumed to already provide adequate
  detail; policing that is not this endpoint's contract.

---

## 3. Architecture

### 3.1 Data flow (chat-originated objective)

```
POST /chat
  1. Write user's message to DashboardChatMessage (unchanged)
  2. Consolidate the current intake exchange (this message + any trailing consecutive
     is_clarifying_question=True/False exchange since the last resolved objective)
  3. coo.assess_sufficiency(session, consolidated_text, recent_messages)
       -> round 1/2: one Claude call (see 3.2)
       -> round 3+: no call - forced sufficient=true (see 3.2)
     a. insufficient -> write COO's reply as a "coo" DashboardChatMessage with
        is_clarifying_question=True; return {status: "needs_clarification", reply: "..."}
        - nothing enqueued.
     b. sufficient -> enqueue_objective(consolidated_text, ...) as today;
        return {objective_id, status: "queued"} (unchanged contract for this branch)
  ↓ (only on the "sufficient" branch; happens later, in the queue worker process)
receive_objective()
  1. classify_objective(objective, registry) -> ObjectiveClassification   [NEW - one call,
     see 3.3, via whichever DepartmentClassifier is configured]
  2. Derive both the multi-department routing decision AND the single-department TaskProfile
     from that one result (eliminates today's redundant double-classification call)
  3. Everything downstream (dispatch, workflow_engine, decisions, escalations) is unchanged
```

### 3.2 Sufficiency check (`orchestrator/intake.py`, new module)

```python
@dataclass
class SufficiencyAssessment:
    sufficient: bool
    clarifying_question: str | None
    reasoning: str

def assess_sufficiency(
    model_gateway: ModelGateway,
    objective: str,
    recent_messages: list[tuple[str, str]],  # (role, content) pairs, last 10 - same window
                                               # GET /chat already uses
    department_registry: DepartmentRegistry,
    round_number: int,                        # 1, 2, or 3+ - see round logic below
) -> SufficiencyAssessment: ...
```

`COOOrchestrator` gets a thin public method, `assess_sufficiency(session, objective,
recent_messages)`, that computes `round_number` (see below) and delegates to this function -
same delegation pattern `receive_objective()` already uses for `planner.py`/`allocator.py`/
`router.py`/`evaluator.py`.

**The call:** reuses the existing `ModelGateway.generate(prompt) -> str` interface - no new
provider methods. The prompt includes the objective, recent conversation, and each
department's name/purpose/mission/capabilities (so "detailed enough" is judged against what
the swarm can actually do), and asks for JSON:
`{"sufficient": bool, "clarifying_question": string|null, "reasoning": string}`.

**Round logic** (`dashboard_api.py` computes this by counting *trailing* consecutive
`DashboardChatMessage` rows with `is_clarifying_question=True`: walk backward from the most
recent message; the count is how many in a row have that flag set before hitting either a
`coo` reply with the flag unset, or the beginning of the transcript. There is no separate
"session" concept to reset on - `DashboardChatMessage` is one continuous global transcript,
consistent with how `GET /chat`/`chat_history()` already treats it today):

| Round | Trigger | Behavior |
|---|---|---|
| 1 | 0 prior clarifying rounds | Normal call. If insufficient, ask the model's own specific clarifying question. |
| 2 | 1 prior clarifying round | Normal call, but the prompt tells the model this is round 2: if still insufficient, phrase the reply as an explicit choice - *"I still don't have full clarity on [X], but I can proceed with what you've shared - it may affect delivery quality/detail. Want me to proceed as-is, or provide more detail on [X]?"* - not another open question. |
| 3+ | 2 prior clarifying rounds | **No model call.** Force `sufficient=true` in code and proceed with whatever's been gathered. Guarantees termination regardless of what the model would have said. |

**Failure mode:** unparseable/malformed JSON from the round 1/2 call fails toward
`sufficient=False` with a generic fallback question ("Could you provide a bit more detail
about what you'd like the swarm to do?") - proceeding into a real (potentially 10-minute,
billed) task execution on a response we couldn't parse is worse than asking once more.
A network/timeout/provider exception (not a parse failure - an actual call failure) is not
swallowed into either branch; `POST /chat` surfaces a distinct error response so the user
knows to retry, rather than silently proceeding or silently asking a question that didn't
really get evaluated.

**Consolidation:** once resolved (true sufficiency or the round-3 cap), the objective text
handed to `enqueue_objective()` is the full gathered exchange - original request plus all
clarifying Q&A since the last resolved objective - not just the last message typed. A small
helper, `_consolidate_intake_conversation(recent_messages) -> str`, builds this from the
trailing exchange the same round-counting logic already walks.

**Schema addition:** `DashboardChatMessage` gains one nullable column, `is_clarifying_question:
bool` (default `False`), set on rows written by this path. This is the only schema change in
this spec.

### 3.3 Department classification (`orchestrator/classification.py`, new module)

```python
@dataclass
class ObjectiveClassification:
    matched_departments: list[DepartmentDefinition]
    reasoning: str

class DepartmentClassifier(Protocol):
    def classify(
        self, objective: str, registry: DepartmentRegistry
    ) -> ObjectiveClassification: ...

class KeywordDepartmentClassifier:
    """Dev/test default - wraps planner.py's existing keyword-overlap logic UNCHANGED,
    just exposed through this interface. No behavior change, no rewrite of the matching
    code itself - only where it's called from."""
    def classify(self, objective, registry) -> ObjectiveClassification: ...

class LLMDepartmentClassifier:
    """Production: wraps a ModelGateway to make one real classification call per objective."""
    def __init__(self, model_gateway: ModelGateway) -> None: ...
    def classify(self, objective, registry) -> ObjectiveClassification: ...

def create_classifier_from_env(
    model_gateway: ModelGateway, env: Mapping[str, str] | None = None
) -> DepartmentClassifier:
    """DEPARTMENT_CLASSIFIER env var: "keyword" (default) or "llm" - exactly parallel to
    shared.providers.create_provider_from_env()'s MODEL_PROVIDER switch."""
```

`COOOrchestrator.__init__` gains `classifier: DepartmentClassifier = KeywordDepartmentClassifier()`
- a stateless default, so **every existing call site that constructs a `COOOrchestrator`
without passing a classifier needs zero changes.** `apps/api_gateway/main.py` is the one
production call site that wires in `create_classifier_from_env(_model_gateway)` instead of
relying on the bare default.

**`receive_objective()` changes:** replace the current two calls
(`select_all_matching_departments()` then, for the single-department path, `analyze_objective()`
- which internally re-derives the same match) with exactly one call to
`classifier.classify(objective, self._departments)`. Both the multi-department routing
decision and the single-department `TaskProfile` are built from that one
`ObjectiveClassification`. `TaskProfile`'s shape is otherwise unchanged (`task_id`,
`objective`, `matched_department`, `reasoning`, `complexity_level` - the last one stays the
existing fixed `"Level 2 Standard"` default; real complexity scoring is part of the deferred
model-tier-selection sub-project, not this one). `match_score` (a keyword-overlap count with
no LLM-classification equivalent) is dropped - confirmed unused outside `planner.py` itself
before removing it.

**What's preserved unchanged:**
- Departments with no assigned agents are filtered out *before* the classifier ever sees them
  (preserves the empty-roster "Strategy Department" fix - a structural guarantee, not
  something left to the model to get right on its own).
- The fixed canonical department order (Research -> Engineering -> Compliance -> Operations)
  still determines execution *sequence* once departments are chosen - the classifier decides
  *which* departments, never what order to run them in (no dependency-graph mechanism exists
  to derive real ordering from; unchanged from today).
- An empty classification result still raises `NoMatchingDepartmentError` - `/objectives`'s
  400 response and the existing escalation-writing path are untouched.
- Malformed/unparseable classifier JSON, or department IDs that don't exist in the real
  registry (hallucinated), do not silently become "no match" - a parse failure raises and
  becomes a technical-failure escalation (existing catch-all in `controller.py`); a
  hallucinated ID is simply dropped from the result before it reaches anything downstream.

---

## 4. Error Handling Summary

| Failure | Where | Behavior |
|---|---|---|
| Sufficiency call: network/timeout/provider error | `POST /chat` | Distinct error response - not silently swallowed into either sufficient/insufficient branch. |
| Sufficiency call: unparseable JSON | `POST /chat` | Fail toward `sufficient=False`, generic fallback clarifying question. |
| Classifier call: any exception | `receive_objective()` | Wrapped the same way `dispatch()`/`execute_workflow()` already are elsewhere in this method: writes a Decision Record + `TECHNICAL_FAILURE` escalation, then re-raises. The re-raise still reaches `queue_worker.py`'s existing catch-all, which marks the objective `failed` (visible via `GET /objectives/{id}/result`) - but now with a full audit trail instead of nothing. (Caught during the implementation plan's self-review - the first draft let this propagate with no record written at all.) |
| Classifier: empty result | `receive_objective()` | `NoMatchingDepartmentError`, unchanged from today. |
| Classifier: hallucinated department ID | `classify_objective()` | Dropped before use, not trusted. |

---

## 5. Testing Strategy

Smaller than it first appeared, specifically because of the "keyword classifier stays the
default" decision:

- **Zero changes needed** for existing tests that construct `COOOrchestrator` without
  specifying a classifier - `KeywordDepartmentClassifier` preserves the exact deterministic
  behavior they already assert on, and wraps rather than rewrites the existing matching code.
- **New:** `LLMDepartmentClassifier` - unit tests against a fake `model_gateway` (no real
  network calls, following the exact pattern `AnthropicModelProvider`/`AgentSDKModelProvider`
  established in SDK_MIGRATION_PLAN.md Phase A), plus one gated real-API integration test.
- **New:** `assess_sufficiency` - round 1/2/3 behavior, JSON-parse-failure fallback,
  conversation consolidation, all against a fake gateway.
- **New:** `dashboard_api.py`'s updated `chat_send()` - insufficient path (no enqueue,
  `is_clarifying_question=True` written), sufficient path (consolidated text enqueued), and
  the round-3 forced-proceed path.
- **New, frontend:** `CooChat.jsx` handling the new `{status: "needs_clarification", reply}`
  response shape - must skip the existing result-polling loop entirely on this branch.
  Verified in-browser (gateway + queue worker running as separate processes, same as
  SDK_MIGRATION_PLAN.md Phase B's verification), not just unit-tested.
- **Unchanged:** `POST /chat/sync`, `POST /objectives`'s existing test coverage for the
  synchronous paths - neither gets the sufficiency check.

---

## 6. Open Items for Future Sub-Projects (explicitly not designed here)

**Deferred, not abandoned.** Splitting these out was a sequencing decision, not a scope cut -
each is substantial enough to deserve its own brainstorm -> spec -> plan cycle, the same
process this document went through. The intended order is roughly the dependency order below
(each later item depends on the ones above it actually working), starting with Department Head
triage once this phase ships:

- Department Head triage (accept current department / reassign to COO / decline as
  not-worth-the-swarm-use-Claude-chat-instead).
- Dynamic agent count and specialist agent selection within a department (possibly building
  on `sdk/agent_builder/` from Phase 10).
- Token/cost budget management as a decision input.
- Real model tier selection (Reasoning Tier Classification, RDL sec.8) replacing the current
  fixed default provider/model for actual task execution - the original ask that started this
  whole design process, and the smallest, most downstream piece of it.
