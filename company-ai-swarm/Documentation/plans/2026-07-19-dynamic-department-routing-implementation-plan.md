# COO Intent Understanding & Sufficiency Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `orchestrator/planner.py`'s keyword-overlap department matcher with a
swappable, real LLM-based classifier (keyword matching kept as the dev/test default), and add
a COO sufficiency check that can ask the user clarifying questions - capped at 3 rounds -
before an objective is ever enqueued.

**Architecture:** Two new orchestrator modules (`classification.py`, `intake.py`) each expose
one pure function/class behind a swappable interface, following the exact
`ModelProvider`/`StubModelProvider` dev-test-vs-production pattern this codebase already uses
everywhere. `COOOrchestrator` gains a `classifier` constructor param (default:
`KeywordDepartmentClassifier()`, so every existing test needs zero changes) and a new
`assess_sufficiency()` method. `apps/api_gateway/dashboard_api.py`'s `POST /chat` calls the
sufficiency check before enqueueing; `POST /chat/sync` and `POST /objectives` are untouched
except that the latter's routing now goes through whichever classifier is configured.

**Tech Stack:** Python 3.11+, SQLAlchemy, FastAPI, pytest, React/JSX (frontend).

**Source spec:** `Documentation/plans/2026-07-19-dynamic-department-routing-design.md` - read
it for the full rationale; this plan only restates what's needed to implement each task.

## Global Constraints

- No real network/API calls in any test except the two gated smoke tests each new module
  gets (skipped by default, matching every existing provider test in this codebase).
- Every existing test that constructs `COOOrchestrator` without a `classifier` kwarg must
  keep passing unmodified - this is the whole point of defaulting to
  `KeywordDepartmentClassifier()`.
- `POST /chat/sync` and `POST /objectives` (EAAS) get zero behavior changes from the
  sufficiency check - it is `POST /chat`-only.
- Run `./.venv/Scripts/python.exe -m pytest Tests/ -q` after every task and confirm the full
  suite passes before committing.
- Follow this repo's existing docstring convention: cite the design-doc section a change
  implements, and explain *why*, not just what.

---

### Task 1: `KeywordDepartmentClassifier` - move existing routing behind a swappable interface

**Files:**
- Create: `services/orchestrator/classification.py`
- Test: `Tests/unit/test_department_classification.py`

**Interfaces:**
- Produces: `ObjectiveClassification` (dataclass: `matched_departments: list[DepartmentDefinition]`, `reasoning: str`), `DepartmentClassifier` (Protocol with `classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification`), `KeywordDepartmentClassifier` (class implementing it).

This task must reproduce `orchestrator/planner.py`'s exact current matching behavior (same
departments matched for the same objectives, same no-agent-department exclusion, same
canonical ordering) - it is a **relocation**, not a rewrite. The current implementation is in
`services/orchestrator/planner.py` (read it before starting - `_tokenize`,
`_department_corpus`, `select_all_matching_departments`, `_CANONICAL_DEPARTMENT_ORDER`).

- [ ] **Step 1: Write the failing test**

Create `Tests/unit/test_department_classification.py`:

```python
"""KeywordDepartmentClassifier must reproduce orchestrator/planner.py's exact existing
matching behavior - this is a relocation of that logic behind a swappable interface
(Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.3), not a
rewrite. Uses the same in-memory DepartmentRegistry construction pattern as
Tests/integration/test_coo_orchestration.py.
"""

from __future__ import annotations

from orchestrator.classification import KeywordDepartmentClassifier, ObjectiveClassification
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry


def _registry(*departments: DepartmentDefinition) -> DepartmentRegistry:
    registry = DepartmentRegistry(".")  # path unused - we populate directly
    for department in departments:
        registry._departments[department.id] = department
    return registry


def test_matches_department_by_keyword_overlap() -> None:
    research = DepartmentDefinition(
        id="research",
        name="Research Department",
        purpose="Information acquisition, analysis, and intelligence generation.",
        mission="Acquire and analyse information required by enterprise objectives.",
        capabilities=["research", "analysis", "reporting"],
        agents=["research_agent_001"],
    )
    registry = _registry(research)

    result = KeywordDepartmentClassifier().classify("Research current market trends.", registry)

    assert isinstance(result, ObjectiveClassification)
    assert [d.id for d in result.matched_departments] == ["research"]
    assert "research" in result.reasoning


def test_excludes_departments_with_no_agents() -> None:
    """The empty-roster fix from orchestrator/planner.py: a department with no agents.yaml
    entries must never be considered a viable match, even if its text scores higher."""

    strategy = DepartmentDefinition(
        id="strategy",
        name="Strategy Department",
        purpose="Market intelligence and strategic planning.",
        mission="Provide market intelligence for enterprise strategy.",
        capabilities=[],
        agents=[],  # no agents - must be excluded
    )
    research = DepartmentDefinition(
        id="research",
        name="Research Department",
        purpose="Information acquisition and analysis.",
        mission="Acquire information.",
        capabilities=["research"],
        agents=["research_agent_001"],
    )
    registry = _registry(strategy, research)

    result = KeywordDepartmentClassifier().classify("Create a market intelligence report", registry)

    assert [d.id for d in result.matched_departments] == ["research"]


def test_no_keyword_overlap_returns_empty_with_reasoning() -> None:
    research = DepartmentDefinition(
        id="research", name="Research Department", purpose="Research.", mission="Research.",
        capabilities=["research"], agents=["research_agent_001"],
    )
    registry = _registry(research)

    result = KeywordDepartmentClassifier().classify("xyz qqq zzz", registry)

    assert result.matched_departments == []
    assert "No department" in result.reasoning


def test_multiple_departments_sorted_in_canonical_order() -> None:
    engineering = DepartmentDefinition(
        id="engineering", name="Engineering Department", purpose="Build systems.",
        mission="Engineering build.", capabilities=["engineering", "build"],
        agents=["engineering_agent_001"],
    )
    research = DepartmentDefinition(
        id="research", name="Research Department", purpose="Research analysis.",
        mission="Research analysis.", capabilities=["research", "analysis"],
        agents=["research_agent_001"],
    )
    registry = _registry(engineering, research)  # inserted out of canonical order

    result = KeywordDepartmentClassifier().classify(
        "Research and build an engineering analysis system", registry
    )

    assert [d.id for d in result.matched_departments] == ["research", "engineering"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest Tests/unit/test_department_classification.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orchestrator.classification'`

- [ ] **Step 3: Write the implementation**

Create `services/orchestrator/classification.py`:

```python
"""Department classification: decides which department(s) an objective belongs to.

Source: Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.3.
Two swappable implementations of one interface - exactly parallel to shared/model_gateway.py's
ModelProvider/StubModelProvider/AnthropicModelProvider pattern:

- KeywordDepartmentClassifier (this task): the exact keyword-overlap logic
  orchestrator/planner.py used to implement directly, relocated here unchanged - not fixed,
  not rewritten. Dev/test default.
- LLMDepartmentClassifier (added in a later task): wraps a ModelGateway to make one real
  classification call per objective. Production, selected via DEPARTMENT_CLASSIFIER=llm.

COOOrchestrator.__init__ defaults to KeywordDepartmentClassifier() - every existing call site
that constructs a COOOrchestrator without specifying a classifier needs zero changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry

_WORD_RE = re.compile(r"[a-zA-Z_]+")
_CANONICAL_DEPARTMENT_ORDER = ["research", "engineering", "compliance", "operations"]


@dataclass
class ObjectiveClassification:
    matched_departments: list[DepartmentDefinition]
    reasoning: str


class DepartmentClassifier(Protocol):
    def classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification: ...


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 3}


def _department_corpus(dept: DepartmentDefinition) -> set[str]:
    text = " ".join([dept.name, dept.purpose, dept.mission, *dept.capabilities])
    return _tokenize(text)


def _canonical_sort_key(department: DepartmentDefinition) -> int:
    try:
        return _CANONICAL_DEPARTMENT_ORDER.index(department.id)
    except ValueError:
        return len(_CANONICAL_DEPARTMENT_ORDER)


class KeywordDepartmentClassifier:
    """Dev/test default - the exact keyword-overlap matching orchestrator/planner.py
    implemented directly before this module existed (see
    Documentation/operations/technology_decisions.md's "Objective-to-department routing"
    note for its known weakness, preserved verbatim here, not fixed). Departments with no
    assigned agents are excluded from consideration entirely - a department the COO cannot
    dispatch to is not a viable match regardless of text-similarity score."""

    def classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification:
        objective_tokens = _tokenize(objective)
        matched = [
            department
            for department in registry.all()
            if department.agents and len(objective_tokens & _department_corpus(department)) > 0
        ]
        matched.sort(key=_canonical_sort_key)

        if not matched:
            reasoning = (
                "No department's capabilities, purpose, or mission shared any keyword with "
                "the objective. Cannot route without a human-specified department."
            )
        else:
            reasoning = (
                f"Matched {len(matched)} department(s) via keyword overlap: "
                f"{[d.id for d in matched]}."
            )

        return ObjectiveClassification(matched_departments=matched, reasoning=reasoning)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest Tests/unit/test_department_classification.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add services/orchestrator/classification.py Tests/unit/test_department_classification.py
git commit -m "Add KeywordDepartmentClassifier: swappable interface for department routing

Relocates orchestrator/planner.py's keyword-overlap matching behind a
DepartmentClassifier interface, unchanged - a later task swaps
COOOrchestrator over to use it. Per Documentation/plans/
2026-07-19-dynamic-department-routing-design.md Section 3.3."
```

---

### Task 2: `LLMDepartmentClassifier` - real Claude-backed classification

**Files:**
- Create: `services/shared/llm_json.py`
- Modify: `services/orchestrator/classification.py`
- Test: `Tests/integration/test_llm_department_classifier.py`

**Interfaces:**
- Consumes: `ObjectiveClassification`, `DepartmentClassifier` (Task 1); `ModelGateway.generate(*, requester: str, prompt: str) -> str` (`services/shared/model_gateway.py`, existing).
- Produces: `strip_code_fence(text: str) -> str` (shared/llm_json.py); `LLMDepartmentClassifier`, `DepartmentClassificationError`, `create_classifier_from_env(model_gateway, env=None) -> DepartmentClassifier` (classification.py).

- [ ] **Step 1: Write the failing test**

Create `Tests/integration/test_llm_department_classifier.py`:

```python
"""LLMDepartmentClassifier makes one real Claude call per objective, using a fake
ModelGateway so no real API call or credentials are required to run these in CI - same
pattern as Tests/integration/test_anthropic_provider.py's fake client_factory. A separate,
gated test at the bottom makes one real call.
"""

from __future__ import annotations

import json
import os

import pytest

from orchestrator.classification import (
    DepartmentClassificationError,
    LLMDepartmentClassifier,
    create_classifier_from_env,
)
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from shared.model_gateway import ModelGateway


class _FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response_text


def _registry(*departments: DepartmentDefinition) -> DepartmentRegistry:
    registry = DepartmentRegistry(".")
    for department in departments:
        registry._departments[department.id] = department
    return registry


def _forex_registry() -> DepartmentRegistry:
    return _registry(
        DepartmentDefinition(
            id="research", name="Research Department", purpose="Information acquisition.",
            mission="Acquire information.", capabilities=["research"], agents=["research_agent_001"],
        ),
        DepartmentDefinition(
            id="engineering", name="Engineering Department", purpose="Build systems.",
            mission="Build.", capabilities=["engineering"], agents=["engineering_agent_001"],
        ),
    )


def test_classify_returns_matched_departments_from_model_json() -> None:
    provider = _FakeProvider(json.dumps({"departments": ["research"], "reasoning": "Needs deep research."}))
    gateway = ModelGateway(provider)
    classifier = LLMDepartmentClassifier(gateway)

    result = classifier.classify("Design a Forex trading strategy", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["research"]
    assert result.reasoning == "Needs deep research."
    assert "Forex" in provider.prompts[0]
    assert "research" in provider.prompts[0]  # department descriptions were included


def test_classify_strips_markdown_code_fence() -> None:
    payload = json.dumps({"departments": ["engineering"], "reasoning": "Build work."})
    provider = _FakeProvider(f"```json\n{payload}\n```")
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    result = classifier.classify("Build the thing", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["engineering"]


def test_classify_drops_hallucinated_department_ids() -> None:
    provider = _FakeProvider(
        json.dumps({"departments": ["research", "made_up_department"], "reasoning": "..."})
    )
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    result = classifier.classify("obj", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["research"]


def test_classify_empty_departments_list_is_a_valid_no_match() -> None:
    provider = _FakeProvider(json.dumps({"departments": [], "reasoning": "Out of scope."}))
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    result = classifier.classify("What's the weather?", _forex_registry())

    assert result.matched_departments == []
    assert result.reasoning == "Out of scope."


def test_classify_raises_on_unparseable_response() -> None:
    provider = _FakeProvider("this is not json at all")
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    with pytest.raises(DepartmentClassificationError):
        classifier.classify("obj", _forex_registry())


def test_classify_raises_on_generate_failure() -> None:
    class _FailingProvider:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("rate limited")

    classifier = LLMDepartmentClassifier(ModelGateway(_FailingProvider()))

    with pytest.raises(DepartmentClassificationError, match="rate limited"):
        classifier.classify("obj", _forex_registry())


def test_create_classifier_from_env_selects_keyword_by_default() -> None:
    from orchestrator.classification import KeywordDepartmentClassifier

    classifier = create_classifier_from_env(ModelGateway(_FakeProvider("{}")), env={})
    assert isinstance(classifier, KeywordDepartmentClassifier)


def test_create_classifier_from_env_selects_llm() -> None:
    classifier = create_classifier_from_env(
        ModelGateway(_FakeProvider("{}")), env={"DEPARTMENT_CLASSIFIER": "llm"}
    )
    assert isinstance(classifier, LLMDepartmentClassifier)


def test_create_classifier_from_env_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unknown DEPARTMENT_CLASSIFIER"):
        create_classifier_from_env(ModelGateway(_FakeProvider("{}")), env={"DEPARTMENT_CLASSIFIER": "made_up"})


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("RUN_REAL_ANTHROPIC_SMOKE_TEST") == "1"),
    reason="Real Claude API smoke test - set ANTHROPIC_API_KEY and RUN_REAL_ANTHROPIC_SMOKE_TEST=1 to run",
)
def test_real_llm_classification_smoke_test() -> None:
    from shared.providers.anthropic_provider import AnthropicModelProvider

    gateway = ModelGateway(AnthropicModelProvider())
    classifier = LLMDepartmentClassifier(gateway)

    result = classifier.classify("Research current renewable energy storage trends", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["research"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_llm_department_classifier.py -v`
Expected: FAIL with `ImportError: cannot import name 'LLMDepartmentClassifier'`

- [ ] **Step 3: Write the implementation**

Create `services/shared/llm_json.py`:

```python
"""Small shared helper for parsing JSON that Claude sometimes wraps in a markdown code
fence even when explicitly told to respond with only JSON. Used by both
orchestrator/classification.py's LLMDepartmentClassifier and orchestrator/intake.py's
assess_sufficiency() - factored out once, rather than duplicated in each."""

from __future__ import annotations

import re

_OPENING_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?")
_CLOSING_FENCE_RE = re.compile(r"\n?```$")


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _OPENING_FENCE_RE.sub("", stripped)
        stripped = _CLOSING_FENCE_RE.sub("", stripped)
    return stripped.strip()
```

Modify `services/orchestrator/classification.py` - add these imports at the top (after the
existing `from typing import Protocol` line):

```python
import json
import os
from typing import Mapping

from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway
```

Append to the end of `services/orchestrator/classification.py`:

```python
class DepartmentClassificationError(Exception):
    """Raised when LLMDepartmentClassifier's call fails or its response can't be parsed."""


class LLMDepartmentClassifier:
    """Production: one real Claude call per objective, via the same ModelGateway swarm
    agents already use - no new tiering axis (Documentation/plans/
    2026-07-19-dynamic-department-routing-design.md Section 2 scope note: model tier
    selection is deferred, separate future work). Reuses ModelGateway.generate(prompt) -> str
    (no new provider methods); asks for JSON, parses it, and drops any department ID the
    model names that isn't in the real registry rather than trusting it."""

    def __init__(self, model_gateway: ModelGateway) -> None:
        self._model_gateway = model_gateway

    def classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification:
        eligible = [d for d in registry.all() if d.agents]
        if not eligible:
            return ObjectiveClassification(
                matched_departments=[],
                reasoning="No department in the registry has any assigned agents.",
            )

        department_descriptions = "\n".join(
            f"- {d.id}: {d.name}. Purpose: {d.purpose}. Mission: {d.mission}. "
            f"Capabilities: {', '.join(d.capabilities) or 'none listed'}."
            for d in eligible
        )
        prompt = (
            "You are classifying a business objective to determine which department(s) of "
            "a company should handle it. Consider what the objective actually requires, not "
            "just literal keyword overlap - for example, a Forex trading strategy request "
            "may require deep research even if the word \"research\" never appears.\n\n"
            f"Objective:\n{objective}\n\n"
            f"Available departments:\n{department_descriptions}\n\n"
            "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
            '{"departments": ["<department_id>", ...], "reasoning": "<one or two '
            'sentences>"}\n'
            'Use an empty list for "departments" if the objective genuinely does not '
            "belong to any of the departments listed above."
        )

        try:
            raw = self._model_gateway.generate(requester="coo:classify", prompt=prompt)
        except Exception as exc:  # noqa: BLE001 - re-raised as a classification error
            raise DepartmentClassificationError(f"Classification call failed: {exc}") from exc

        try:
            data = json.loads(strip_code_fence(raw))
            department_ids = data["departments"]
            reasoning = data["reasoning"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise DepartmentClassificationError(
                f"Classifier response was not valid JSON in the expected shape: {raw!r}"
            ) from exc

        eligible_ids = {d.id for d in eligible}
        matched = [d for d in eligible if d.id in department_ids and d.id in eligible_ids]
        matched.sort(key=_canonical_sort_key)

        return ObjectiveClassification(matched_departments=matched, reasoning=reasoning)


_CLASSIFIERS = ("keyword", "llm")


def create_classifier_from_env(
    model_gateway: ModelGateway, env: Mapping[str, str] | None = None
) -> DepartmentClassifier:
    """DEPARTMENT_CLASSIFIER env var: "keyword" (default) or "llm" - exactly parallel to
    shared.providers.create_provider_from_env()'s MODEL_PROVIDER switch."""

    source = env if env is not None else os.environ
    selected = source.get("DEPARTMENT_CLASSIFIER", "keyword").strip().lower()

    if selected == "keyword":
        return KeywordDepartmentClassifier()
    if selected == "llm":
        return LLMDepartmentClassifier(model_gateway)

    raise ValueError(f"Unknown DEPARTMENT_CLASSIFIER={selected!r}; expected one of {_CLASSIFIERS}.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_llm_department_classifier.py -v`
Expected: PASS (9 tests, 1 skipped)

- [ ] **Step 5: Commit**

```bash
git add services/shared/llm_json.py services/orchestrator/classification.py \
        Tests/integration/test_llm_department_classifier.py
git commit -m "Add LLMDepartmentClassifier and DEPARTMENT_CLASSIFIER env var

Real Claude-backed department classification, selected via
create_classifier_from_env() - mirrors shared/providers/__init__.py's
create_provider_from_env() pattern exactly. Per Documentation/plans/
2026-07-19-dynamic-department-routing-design.md Section 3.3."
```

---

### Task 3: Wire the classifier into `COOOrchestrator` and delete the superseded planner.py code

**Files:**
- Modify: `services/orchestrator/controller.py`
- Modify: `services/orchestrator/planner.py`
- Modify: `apps/api_gateway/main.py:42-43,55-70`
- Test: existing suite (no new test file - this task is a refactor proven by the existing suite still passing)

**Interfaces:**
- Consumes: `DepartmentClassifier`, `KeywordDepartmentClassifier`, `ObjectiveClassification`, `create_classifier_from_env` (Tasks 1-2).
- Produces: `COOOrchestrator(..., classifier: DepartmentClassifier = KeywordDepartmentClassifier())`; `receive_objective()` now calls `self._classifier.classify(...)` exactly once.

**Why this task has no new test file:** it's a pure refactor - the *existing* ~10 test files
that construct `COOOrchestrator` and route objectives through it are the regression suite.
If they all still pass, the refactor is correct.

- [ ] **Step 1: Confirm the current suite passes before touching anything**

Run: `./.venv/Scripts/python.exe -m pytest Tests/ -q`
Expected: `210 passed, 2 skipped` (or whatever the current baseline is - record the number)

- [ ] **Step 2: Update `services/orchestrator/controller.py`**

Replace the import block (lines 48-59):

```python
from orchestrator import decisions, escalations
from orchestrator.allocator import select_agent
from orchestrator.classification import DepartmentClassifier, KeywordDepartmentClassifier
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.evaluator import OutcomeValidation, validate_outcome
from orchestrator.router import dispatch
from security_service.audit import write_audit_record
from shared.model_gateway import ModelGateway
from workflow_engine.engine import REVIEW_DEPARTMENT_ID, execute_workflow
from workflow_engine.gate_integrity import check_gate_integrity
from workflow_engine.models import WorkflowRun
```

(This drops `from orchestrator.planner import TaskProfile, analyze_objective,
select_all_matching_departments` and adds the two classification imports.)

`TaskProfile` was imported from `planner` for the `ObjectiveOutcome.task_profile` type hint -
replace it with a new, smaller dataclass defined directly in `controller.py`, right after the
`NoMatchingDepartmentError` class (around line 63):

```python
@dataclass
class TaskProfile:
    """Replaces orchestrator/planner.py's TaskProfile (Documentation/plans/
    2026-07-19-dynamic-department-routing-design.md Section 3.3) - same fields except
    match_score is dropped (a keyword-overlap count with no LLM-classification equivalent;
    confirmed unused outside planner.py before removing it)."""

    task_id: str
    objective: str
    complexity_level: str
    matched_department: DepartmentDefinition | None
    reasoning: str
```

Update `COOOrchestrator.__init__` (currently lines 91-104):

```python
class COOOrchestrator:
    def __init__(
        self,
        *,
        coo_id: str,
        department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        telemetry: TelemetrySink | None = None,
        classifier: DepartmentClassifier = KeywordDepartmentClassifier(),
    ) -> None:
        self.coo_id = coo_id
        self._departments = department_registry
        self._agents = agent_registry
        self._model_gateway = model_gateway
        self._telemetry = telemetry
        self._classifier = classifier
```

Replace the routing section of `receive_objective()` (currently lines 106-156, from the
docstring comment through `task_profile = analyze_objective(objective, self._departments)`
just before "# Select Agents"):

```python
    def receive_objective(
        self, session: Session, objective: str, *, required_output: str
    ) -> ObjectiveOutcome | WorkflowObjectiveOutcome:
        decision_id = f"DEC-{uuid4().hex[:8]}"

        # Understand Intent -> Classify Task -> Assess Complexity -> Identify Capabilities
        # -> Select Departments. One classification call (Documentation/plans/
        # 2026-07-19-dynamic-department-routing-design.md Section 3.3) replaces what used
        # to be two separate keyword-matching calls (select_all_matching_departments() then,
        # for the single-department path, a second internal match inside analyze_objective())
        # - wasteful even when both were free, and actively costly now that a real classifier
        # may make a network call. Both the multi-department decision and the
        # single-department TaskProfile are derived from this one result.
        #
        # Phase 8 fix (unchanged): a lone match on "operations" (the Review Agent's
        # department) must NOT take the single-agent shortcut - it would dispatch the
        # original objective straight to the Review Agent as if it were primary work,
        # contradicting review_agent/agent.yaml's own mission ("does not perform the
        # original work it reviews"). Routed through the Workflow Engine instead, same as
        # any other multi-department match.
        try:
            classification = self._classifier.classify(objective, self._departments)
        except Exception as exc:
            # Mirrors dispatch()'s and execute_workflow()'s existing failure handling further
            # down this method (and in _receive_multi_department_objective) - a classifier
            # failure must leave the same audit trail (Decision Record + TECHNICAL_FAILURE
            # escalation) any other technical failure does, not silently propagate with
            # nothing written. Found during this plan's self-review: the first draft let this
            # raise before any record existed at all.
            decisions.write_decision(
                session,
                id=decision_id,
                objective=objective,
                reasoning=f"Classification failed: {type(exc).__name__}: {exc}",
                chosen_action="reject: classification failed",
            )
            escalations.write_escalation(
                session,
                condition=EscalationCondition.TECHNICAL_FAILURE,
                reasoning=f"{type(exc).__name__}: {exc}",
                decision_id=decision_id,
                is_technical_failure=True,
            )
            raise

        matched_departments = classification.matched_departments
        routes_through_workflow_engine = len(matched_departments) > 1 or (
            len(matched_departments) == 1 and matched_departments[0].id == REVIEW_DEPARTMENT_ID
        )

        if not matched_departments:
            decisions.write_decision(
                session,
                id=decision_id,
                objective=objective,
                reasoning=classification.reasoning,
                chosen_action="reject: no matching department",
            )
            escalations.write_escalation(
                session,
                condition=EscalationCondition.NO_MATCHING_DEPARTMENT,
                reasoning=classification.reasoning,
                decision_id=decision_id,
            )
            raise NoMatchingDepartmentError(classification.reasoning)

        if routes_through_workflow_engine:
            return self._receive_multi_department_objective(
                session,
                objective,
                required_output=required_output,
                decision_id=decision_id,
                matched_departments=matched_departments,
            )

        task_profile = TaskProfile(
            task_id=f"TSK-{uuid4().hex[:8]}",
            objective=objective,
            # Fixed default - real complexity scoring is deferred (design doc Section 2);
            # unchanged from orchestrator/planner.py's original placeholder.
            complexity_level="Level 2 Standard",
            matched_department=matched_departments[0],
            reasoning=classification.reasoning,
        )
```

Everything from `# Select Agents` (previously line 158) through the end of
`receive_objective()` (previously line 239) is unchanged - `task_profile.matched_department`
and `task_profile.reasoning` are still valid attribute accesses on the new `TaskProfile`.

- [ ] **Step 3: Delete the superseded functions from `services/orchestrator/planner.py`**

Delete `select_best_matching_department`, `select_all_matching_departments`,
`analyze_objective`, and the `TaskProfile` dataclass from `services/orchestrator/planner.py`
(everything except the module docstring, `_WORD_RE`, `_tokenize`, `_department_corpus`, and
`_CANONICAL_DEPARTMENT_ORDER` is now dead code, superseded by
`services/orchestrator/classification.py`). If nothing outside `planner.py` itself imports
`_tokenize`/`_department_corpus`/`_WORD_RE`/`_CANONICAL_DEPARTMENT_ORDER` either (they were
copied into `classification.py`, not imported from here), delete the whole file:

```bash
git rm services/orchestrator/planner.py
```

Before deleting, confirm nothing else imports from it:

```bash
grep -rn "orchestrator.planner\|from planner import" --include="*.py" . | grep -v "^\./Documentation"
```

Expected: no output (only doc/comment mentions in other files' docstrings, which don't
`import` anything and don't need editing).

- [ ] **Step 4: Update `apps/api_gateway/main.py`**

Modify the import block (line 43, add one line after it):

```python
from orchestrator.classification import create_classifier_from_env
from shared.providers import create_provider_from_env
```

Modify the `_coo` construction (currently lines 55-70):

```python
_telemetry = TelemetrySink()
# MODEL_PROVIDER env var selects stub (default, no credentials) / anthropic (API-key
# billing) / agent_sdk (subscription-capable) - see shared/providers/__init__.py and
# Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.1.
_model_gateway = ModelGateway(create_provider_from_env(), telemetry=_telemetry)
_department_registry = DepartmentRegistry(_REPO_ROOT / "departments")
_department_registry.load_all()
_agent_registry = AgentRegistry(_REPO_ROOT / "agents" / "active")
_agent_registry.load_all()
_coo = COOOrchestrator(
    coo_id="coo",
    department_registry=_department_registry,
    agent_registry=_agent_registry,
    model_gateway=_model_gateway,
    telemetry=_telemetry,
    # DEPARTMENT_CLASSIFIER env var selects keyword (default, no credentials) / llm (real
    # Claude-backed routing) - see orchestrator/classification.py and Documentation/plans/
    # 2026-07-19-dynamic-department-routing-design.md Section 3.3.
    classifier=create_classifier_from_env(_model_gateway),
)
```

- [ ] **Step 5: Write and run a test proving classifier failures get a full audit trail**

This is the fix from this plan's own self-review: a classifier exception must produce a
Decision Record + `TECHNICAL_FAILURE` escalation before re-raising, exactly like `dispatch()`
and `execute_workflow()` failures already do elsewhere in this same method.

Create `Tests/integration/test_classifier_failure_escalation.py`:

```python
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
```

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_classifier_failure_escalation.py -v`
Expected: PASS (1 test). If `EscalationCondition.TECHNICAL_FAILURE`'s exact enum value or
`list_pending_escalations`'s exact return shape differs from what's assumed here, check
`services/orchestrator/escalation.py` and `services/orchestrator/escalations.py` directly and
adjust the assertions to match - the behavior being tested (record written, then re-raise) is
what matters, not these exact accessor names.

- [ ] **Step 6: Run the full suite and fix any fallout**

Run: `./.venv/Scripts/python.exe -m pytest Tests/ -q`
Expected: same pass count as Step 1's baseline + 1 new test, 0 failures. If anything fails, it
is most likely one of these two things - check them first:
- A test importing `TaskProfile` from `orchestrator.controller` (not `orchestrator.planner`)
  needs no change, since it's still exported from `controller.py`; a test importing it from
  `orchestrator.planner` needs its import updated to `from orchestrator.controller import TaskProfile`.
- A test asserting on `models_used=["stub"]` or an exact old reasoning string - none were
  found during planning (`grep -rn "Matched department\|keyword-overlap" Tests/` returned no
  hits), but re-run that grep if something fails here to confirm.

- [ ] **Step 7: Commit**

```bash
git add services/orchestrator/controller.py apps/api_gateway/main.py \
        Tests/integration/test_classifier_failure_escalation.py
git rm services/orchestrator/planner.py
git commit -m "Wire DepartmentClassifier into COOOrchestrator; delete superseded planner.py

receive_objective() now calls the classifier exactly once (was two
redundant keyword-matching calls) and derives both the multi-department
decision and the single-department TaskProfile from that one result. A
classifier failure gets a Decision Record + TECHNICAL_FAILURE escalation
before re-raising, matching dispatch()/execute_workflow()'s existing
pattern. classifier defaults to KeywordDepartmentClassifier() so every
existing test that constructs a COOOrchestrator needs zero changes. main.py
wires DEPARTMENT_CLASSIFIER env var the same way MODEL_PROVIDER already works.
Per Documentation/plans/2026-07-19-dynamic-department-routing-design.md
Section 3.3."
```

---

### Task 4: `orchestrator/intake.py` - the sufficiency check

**Files:**
- Create: `services/orchestrator/intake.py`
- Test: `Tests/unit/test_intake_sufficiency.py`

**Interfaces:**
- Consumes: `ModelGateway.generate(*, requester: str, prompt: str) -> str`; `strip_code_fence` (Task 2); `DepartmentRegistry` (existing).
- Produces: `SufficiencyAssessment` (dataclass: `sufficient: bool`, `clarifying_question: str | None`, `reasoning: str`), `assess_sufficiency(model_gateway, objective, recent_messages, department_registry, round_number) -> SufficiencyAssessment`, `FALLBACK_CLARIFYING_QUESTION: str`.

- [ ] **Step 1: Write the failing test**

Create `Tests/unit/test_intake_sufficiency.py`:

```python
"""orchestrator/intake.py's assess_sufficiency() round logic (Documentation/plans/
2026-07-19-dynamic-department-routing-design.md Section 3.2), against a fake ModelGateway -
no real API calls."""

from __future__ import annotations

import json

import pytest

from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.intake import FALLBACK_CLARIFYING_QUESTION, assess_sufficiency
from shared.model_gateway import ModelGateway


class _FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response_text


def _registry() -> DepartmentRegistry:
    registry = DepartmentRegistry(".")
    registry._departments["research"] = DepartmentDefinition(
        id="research", name="Research Department", purpose="Information acquisition.",
        mission="Acquire information.", capabilities=["research"], agents=["research_agent_001"],
    )
    return registry


def test_round_1_sufficient() -> None:
    provider = _FakeProvider(json.dumps({"sufficient": True, "clarifying_question": None, "reasoning": "Clear enough."}))
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "Research current market trends.", [], _registry(), round_number=1)

    assert result.sufficient is True
    assert result.clarifying_question is None


def test_round_1_insufficient_asks_the_models_question() -> None:
    provider = _FakeProvider(
        json.dumps({"sufficient": False, "clarifying_question": "Which market segment?", "reasoning": "Too vague."})
    )
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "Do some research", [], _registry(), round_number=1)

    assert result.sufficient is False
    assert result.clarifying_question == "Which market segment?"


def test_round_2_prompt_asks_for_choice_framing() -> None:
    """Round 2's prompt must instruct the model to phrase an insufficient verdict as an
    explicit choice, not another open question - the test can't control what a real model
    outputs, but it can assert the instruction was actually sent."""

    provider = _FakeProvider(
        json.dumps({"sufficient": False, "clarifying_question": "Proceed as-is or provide detail?", "reasoning": "Still vague."})
    )
    gateway = ModelGateway(provider)

    assess_sufficiency(gateway, "Do some research", [("user", "Do some research")], _registry(), round_number=2)

    assert "explicit choice" in provider.prompts[0]
    assert "proceed" in provider.prompts[0].lower()


def test_round_3_never_calls_the_model() -> None:
    provider = _FakeProvider("should never be read")
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "obj", [], _registry(), round_number=3)

    assert result.sufficient is True
    assert provider.prompts == []


def test_round_4_and_beyond_also_never_calls_the_model() -> None:
    provider = _FakeProvider("should never be read")
    result = assess_sufficiency(ModelGateway(provider), "obj", [], _registry(), round_number=5)

    assert result.sufficient is True
    assert provider.prompts == []


def test_unparseable_json_fails_toward_insufficient_with_fallback() -> None:
    provider = _FakeProvider("this is not json")
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "obj", [], _registry(), round_number=1)

    assert result.sufficient is False
    assert result.clarifying_question == FALLBACK_CLARIFYING_QUESTION


def test_missing_expected_keys_fails_toward_insufficient() -> None:
    provider = _FakeProvider(json.dumps({"unexpected": "shape"}))
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "obj", [], _registry(), round_number=1)

    assert result.sufficient is False
    assert result.clarifying_question == FALLBACK_CLARIFYING_QUESTION


def test_generate_failure_propagates_not_swallowed() -> None:
    """A network/timeout/provider failure is an infrastructure problem, not a 'the model
    said no' verdict - it must raise, not be silently converted into a fabricated
    clarifying question (Documentation/plans/2026-07-19-dynamic-department-routing-design.md
    Section 4's error table)."""

    class _FailingProvider:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("connection reset")

    gateway = ModelGateway(_FailingProvider())

    with pytest.raises(RuntimeError, match="connection reset"):
        assess_sufficiency(gateway, "obj", [], _registry(), round_number=1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest Tests/unit/test_intake_sufficiency.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orchestrator.intake'`

- [ ] **Step 3: Write the implementation**

Create `services/orchestrator/intake.py`:

```python
"""Sufficiency check: does the COO have enough detail to act on an objective, or should it
ask the user a clarifying question first?

Source: Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.2.
Chat-specific pre-flight logic - called from apps/api_gateway/dashboard_api.py's POST /chat,
before anything is ever enqueued. POST /chat/sync and POST /objectives (EAAS) do not use
this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from orchestrator.department_registry import DepartmentRegistry
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway

FALLBACK_CLARIFYING_QUESTION = (
    "Could you provide a bit more detail about what you'd like the swarm to do?"
)


@dataclass
class SufficiencyAssessment:
    sufficient: bool
    clarifying_question: str | None
    reasoning: str


def assess_sufficiency(
    model_gateway: ModelGateway,
    objective: str,
    recent_messages: list[tuple[str, str]],
    department_registry: DepartmentRegistry,
    round_number: int,
) -> SufficiencyAssessment:
    """`round_number` is 1-indexed, computed by the caller (apps/api_gateway/dashboard_api.py
    counts trailing consecutive is_clarifying_question=True DashboardChatMessage rows + 1).
    Round 3+ never calls the model - forces sufficient=True in code, guaranteeing the
    clarification loop terminates regardless of what the model would have said.

    A model-call failure (network/timeout/provider error) is NOT caught here - it propagates
    to the caller, which must surface a distinct error rather than silently treat it as an
    'insufficient' verdict. An unparseable/malformed *response* (the call succeeded, but
    didn't return the JSON shape asked for) IS caught, and fails toward insufficient with a
    generic fallback question - proceeding into a real task execution on a response we
    couldn't interpret is worse than asking once more."""

    if round_number >= 3:
        return SufficiencyAssessment(
            sufficient=True,
            clarifying_question=None,
            reasoning="Round 3 cap reached - proceeding with the information gathered so far.",
        )

    history_text = "\n".join(f"{role}: {content}" for role, content in recent_messages) or "(none yet)"
    departments_text = "\n".join(
        f"- {d.name}: {d.purpose}" for d in department_registry.all() if d.agents
    )

    if round_number == 1:
        round_instruction = (
            "This is the first time you're assessing this request. If it lacks enough "
            "detail to act on, ask one specific clarifying question about what's missing."
        )
    else:
        round_instruction = (
            "You have already asked one clarifying question about this request and the "
            "user has replied, but it is still not enough to act on confidently. Do NOT ask "
            "another open-ended question. Instead, phrase your reply as an explicit choice: "
            "offer to proceed with what has been shared so far (noting this may affect "
            "delivery quality or detail), or ask specifically for the one piece of "
            "information still missing."
        )

    prompt = (
        "You are the Chief Operating Officer of an AI company, deciding whether a user's "
        "request has enough detail to hand off to a department for execution.\n\n"
        f"Departments available:\n{departments_text}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Latest request:\n{objective}\n\n"
        f"{round_instruction}\n\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"sufficient": true|false, "clarifying_question": "<string, or null if sufficient>", '
        '"reasoning": "<one sentence>"}'
    )

    # Deliberately not caught here - see this function's docstring.
    raw = model_gateway.generate(requester="coo:sufficiency", prompt=prompt)

    try:
        data = json.loads(strip_code_fence(raw))
        sufficient = bool(data["sufficient"])
        clarifying_question = data.get("clarifying_question")
        reasoning = data["reasoning"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return SufficiencyAssessment(
            sufficient=False,
            clarifying_question=FALLBACK_CLARIFYING_QUESTION,
            reasoning=f"Could not parse the sufficiency check's response ({exc}); asking for more detail.",
        )

    if sufficient:
        return SufficiencyAssessment(sufficient=True, clarifying_question=None, reasoning=reasoning)

    return SufficiencyAssessment(
        sufficient=False,
        clarifying_question=clarifying_question or FALLBACK_CLARIFYING_QUESTION,
        reasoning=reasoning,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest Tests/unit/test_intake_sufficiency.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add services/orchestrator/intake.py Tests/unit/test_intake_sufficiency.py
git commit -m "Add orchestrator/intake.py: COO sufficiency check with 3-round cap

assess_sufficiency() - round 1 asks a normal clarifying question if
insufficient; round 2 reframes as an explicit proceed-or-detail choice;
round 3+ never calls the model, forcing sufficient=True to guarantee
termination. Model-call failures propagate (infrastructure problem);
unparseable responses fail toward insufficient with a fallback question.
Per Documentation/plans/2026-07-19-dynamic-department-routing-design.md
Section 3.2."
```

---

### Task 5: `COOOrchestrator.assess_sufficiency()` + `is_clarifying_question` schema column

**Files:**
- Modify: `services/orchestrator/controller.py`
- Modify: `apps/api_gateway/dashboard_api.py:74-83` (the `DashboardChatMessage` model)
- Test: `Tests/integration/test_coo_orchestration.py` (add one test; existing tests unaffected)

**Interfaces:**
- Consumes: `orchestrator.intake.assess_sufficiency`, `SufficiencyAssessment` (Task 4).
- Produces: `COOOrchestrator.assess_sufficiency(self, objective: str, recent_messages: list[tuple[str, str]], *, round_number: int) -> SufficiencyAssessment`; `DashboardChatMessage.is_clarifying_question: bool`.

- [ ] **Step 1: Write the failing test**

Add to `Tests/integration/test_coo_orchestration.py` (append; read the file first to match
its existing fixture style - it already has a `coo`-building fixture per the Task 1 grep):

```python
def test_assess_sufficiency_delegates_to_intake_with_configured_departments() -> None:
    """COOOrchestrator.assess_sufficiency() is a thin wrapper - this proves it actually
    reaches a real model_gateway call and returns a SufficiencyAssessment, using the same
    StubModelProvider-backed COO every other test in this file builds. StubModelProvider's
    fixed text isn't parseable JSON, so this exercises the 'fails toward insufficient with
    fallback question' path - a real assertion, not a placeholder."""

    from orchestrator.intake import FALLBACK_CLARIFYING_QUESTION, SufficiencyAssessment

    coo = _build_coo()  # existing fixture/helper this test file already has - see Task 1's grep

    result = coo.assess_sufficiency("Do something", [], round_number=1)

    assert isinstance(result, SufficiencyAssessment)
    assert result.sufficient is False
    assert result.clarifying_question == FALLBACK_CLARIFYING_QUESTION
```

(If `_build_coo()` isn't the actual existing helper name in this file, use whatever fixture
function/name the file already uses to construct a `COOOrchestrator` - check the file's
existing tests before writing this one.)

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_coo_orchestration.py -v -k assess_sufficiency`
Expected: FAIL with `AttributeError: 'COOOrchestrator' object has no attribute 'assess_sufficiency'`

- [ ] **Step 3: Write the implementation**

In `services/orchestrator/controller.py`, add to the import block:

```python
from orchestrator import intake
```

Add this method to `COOOrchestrator` (anywhere inside the class - e.g., right after
`__init__`):

```python
    def assess_sufficiency(
        self, objective: str, recent_messages: list[tuple[str, str]], *, round_number: int
    ) -> intake.SufficiencyAssessment:
        """Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.2 -
        thin delegation to orchestrator/intake.py, keeping ModelGateway access encapsulated
        inside COOOrchestrator (the same discipline this class already applies to
        receive_objective()'s use of self._model_gateway)."""

        return intake.assess_sufficiency(
            self._model_gateway, objective, recent_messages, self._departments, round_number
        )
```

In `apps/api_gateway/dashboard_api.py`, update the import (line 51):

```python
from sqlalchemy import Boolean, DateTime, String, Text
```

Update `DashboardChatMessage` (currently lines 74-83):

```python
class DashboardChatMessage(Base):
    __tablename__ = "dashboard_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    decision_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.2: set
    # True on "coo" replies written by the sufficiency check, so dashboard_api.py can count
    # trailing consecutive clarifying rounds (the 3-round cap) and distinguish a clarifying
    # question from a normal completed-objective reply.
    is_clarifying_question: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_coo_orchestration.py -v`
Expected: PASS (all tests in the file, including the new one)

- [ ] **Step 5: Delete the stale dev database** (schema changed - `Base.metadata.create_all()`
does not alter existing tables, only creates missing ones; this repo's own established
practice for this exact situation is to delete the dev sqlite file, per the
`.claude/settings.local.json` permission entry for it)

```bash
rm -f apps/api_gateway/api_gateway_dev.sqlite3
```

- [ ] **Step 6: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest Tests/ -q`
Expected: all passing, same count as Task 3's baseline + 1 new test.

- [ ] **Step 7: Commit**

```bash
git add services/orchestrator/controller.py apps/api_gateway/dashboard_api.py \
        Tests/integration/test_coo_orchestration.py
git commit -m "Add COOOrchestrator.assess_sufficiency() and is_clarifying_question column

Thin delegation to orchestrator/intake.py, keeping ModelGateway access
encapsulated in COOOrchestrator. DashboardChatMessage.is_clarifying_question
lets dashboard_api.py (next task) count trailing clarifying rounds. Per
Documentation/plans/2026-07-19-dynamic-department-routing-design.md
Section 3.2."
```

---

### Task 6: Wire the sufficiency check into `POST /chat`

**Files:**
- Modify: `apps/api_gateway/dashboard_api.py:319-360` (add helpers, rewrite `chat_send`)
- Test: `Tests/integration/test_api_gateway_async.py` (add new tests)

**Interfaces:**
- Consumes: `coo.assess_sufficiency(...)` (Task 5); `enqueue_objective` (existing, `objective_queue.py`).
- Produces: `POST /chat` response shape gains a second variant: `{"status": "needs_clarification", "reply": str}` alongside the existing `{"objective_id": str, "status": "queued"}`.

- [ ] **Step 1: Write the failing tests**

Add to `Tests/integration/test_api_gateway_async.py` (append; it already has `_client()` and
`HEADERS` at module level per the existing file):

```python
def test_chat_insufficient_request_asks_a_clarifying_question_without_enqueueing() -> None:
    """StubModelProvider's fixed text isn't parseable JSON, so the default dev/test gateway
    always fails toward 'insufficient' with the fallback question - this test exercises that
    real code path (not a mock standing in for it), same as
    test_coo_orchestration.py's new assess_sufficiency test."""

    client = _client()

    response = client.post("/chat", headers=HEADERS, json={"message": "Do something vague"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert "reply" in body
    assert "objective_id" not in body

    history = client.get("/chat", headers=HEADERS).json()
    assert history["messages"][-1]["role"] == "coo"
    assert history["messages"][-1]["content"] == body["reply"]


def test_chat_third_round_forces_proceed_and_enqueues() -> None:
    """Two clarifying rounds, then a third message must enqueue regardless of what the
    (stub-backed, always-insufficient) sufficiency check would otherwise say."""

    client = _client()

    first = client.post("/chat", headers=HEADERS, json={"message": "round one"})
    assert first.json()["status"] == "needs_clarification"

    second = client.post("/chat", headers=HEADERS, json={"message": "round two"})
    assert second.json()["status"] == "needs_clarification"

    third = client.post("/chat", headers=HEADERS, json={"message": "round three"})
    body = third.json()
    assert body["status"] == "queued"
    assert "objective_id" in body

    # The enqueued objective consolidates the whole exchange, not just "round three".
    gateway_main.drain_queue_once()
    result = client.get(f"/objectives/{body['objective_id']}/result", headers=HEADERS).json()
    assert "round one" in result["objective"]
    assert "round two" in result["objective"]
    assert "round three" in result["objective"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_api_gateway_async.py -v -k "insufficient or third_round"`
Expected: FAIL - `test_chat_insufficient_...` fails because current `/chat` always returns
`{"objective_id", "status": "queued"}` with no sufficiency check yet.

- [ ] **Step 3: Write the implementation**

In `apps/api_gateway/dashboard_api.py`, add these imports (near the top, alongside the
existing `objective_queue` import):

```python
from orchestrator.intake import SufficiencyAssessment
```

Add these two helpers right before `_build_objective_from_chat_body` (around line 319):

```python
def _count_trailing_clarifying_rounds(session: Session, *, limit: int = 20) -> int:
    """How many clarifying questions the COO has already asked in a row, walking backward
    from the most recent message and stopping at the first non-clarifying "coo" reply (or
    the start of the transcript) - see this module's docstring on why there's no separate
    "session" concept to reset on."""

    recent = (
        session.query(DashboardChatMessage)
        .order_by(DashboardChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    count = 0
    for message in recent:
        if message.role != "coo":
            continue
        if message.is_clarifying_question:
            count += 1
        else:
            break
    return count


def _consolidate_intake_conversation(session: Session, *, limit: int = 20) -> str:
    """Builds the full objective text to hand to receive_objective() once the COO decides
    (or is forced) to proceed: the original request plus all clarifying Q&A since the last
    resolved objective, not just the most recent message typed. Assumes the current user
    message has already been written to DashboardChatMessage (chat_send() writes it before
    calling this) - it is always included, since it's the most recent row and has
    role="user", which never matches this loop's break condition."""

    recent = (
        session.query(DashboardChatMessage)
        .order_by(DashboardChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    trailing: list[DashboardChatMessage] = []
    for message in recent:
        if message.role == "coo" and not message.is_clarifying_question:
            break
        trailing.append(message)
    trailing.reverse()  # oldest first

    return "\n".join(f"{m.role}: {m.content}" for m in trailing)
```

Replace `chat_send` (currently lines 336-360):

```python
    @router.post("/chat")
    def chat_send(
        body: dict[str, Any],
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        """Phase B (SDK_MIGRATION_PLAN.md Section 4.2) made this fire-and-forget; this adds
        a sufficiency pre-flight check (Documentation/plans/
        2026-07-19-dynamic-department-routing-design.md) before anything is enqueued.
        Round 1/2: one Claude call via coo.assess_sufficiency(). Round 3+: no call, forced
        sufficient (see orchestrator/intake.py). Insufficient -> writes the COO's clarifying
        question as a coo reply (is_clarifying_question=True) and returns without
        enqueueing. Sufficient -> enqueues the full consolidated exchange, same
        {objective_id, status} contract POST /chat has had since Phase B."""

        objective, required_output = _build_objective_from_chat_body(body)

        user_msg = DashboardChatMessage(role="user", content=objective)
        session.add(user_msg)
        session.commit()

        round_number = _count_trailing_clarifying_rounds(session) + 1
        recent_for_model = [
            (m.role, m.content)
            for m in (
                session.query(DashboardChatMessage)
                .order_by(DashboardChatMessage.id.desc())
                .limit(10)
                .all()
            )
        ][::-1]

        try:
            assessment: SufficiencyAssessment = coo.assess_sufficiency(
                objective, recent_for_model, round_number=round_number
            )
        except Exception as exc:
            # An infrastructure failure (network/timeout/provider error), not a "the model
            # said no" verdict - surfaced distinctly rather than silently treated as either
            # sufficient or insufficient. See orchestrator/intake.py's assess_sufficiency()
            # docstring.
            raise HTTPException(
                status_code=502, detail=f"Could not assess the request: {exc}"
            ) from exc

        if not assessment.sufficient:
            coo_msg = DashboardChatMessage(
                role="coo", content=assessment.clarifying_question, is_clarifying_question=True
            )
            session.add(coo_msg)
            session.commit()
            return {"status": "needs_clarification", "reply": assessment.clarifying_question}

        consolidated_objective = _consolidate_intake_conversation(session)
        record = enqueue_objective(
            session,
            objective=consolidated_objective,
            required_output=required_output,
            submitted_by=DASHBOARD_CHAT_SUBMITTER,
        )

        return {"objective_id": record.id, "status": record.status}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_api_gateway_async.py -v`
Expected: the two new tests PASS; **five pre-existing tests in this same file now FAIL** -
`test_chat_is_fire_and_forget`, `test_result_endpoint_reflects_full_lifecycle`,
`test_chat_history_shows_reply_after_worker_processes_it`,
`test_no_matching_department_completes_not_fails`, and
`test_activity_shows_in_flight_objective_before_draining`. All five predate the sufficiency
check and call `POST /chat` once, expecting immediate enqueueing -
`StubModelProvider`'s fixed placeholder text is never parseable sufficiency JSON, so every
`/chat` call now comes back `needs_clarification` for up to 2 rounds first. This is expected
and fixed in the next step, not a bug to chase.

- [ ] **Step 5: Fix the five pre-existing tests to get past the sufficiency check**

These tests are about the async queue/worker mechanics, not the sufficiency check itself -
`/chat/sync` would dodge the new gate entirely but also skip the queue behavior these tests
exist to prove, so the fix is to get *past* round 1/2 deterministically, not around them.
Replace the entire contents of `Tests/integration/test_api_gateway_async.py` with:

```python
"""Phase B exit-criteria test (Documentation/plans/SDK_MIGRATION_PLAN.md Section 6:
test_api_gateway_async.py "fire-and-forget endpoints, polling result"): the full async
round-trip through the real HTTP layer - POST /chat (fire-and-forget) -> queue worker
processes it -> GET /objectives/{id}/result -> GET /chat shows the eventual reply -> GET
/activity's in_flight_objectives reflects queued/executing/settled states.

Uses `main.drain_queue_once()` to force one worker cycle deterministically instead of
sleeping and hoping a background thread got to it - see main.py's comment on why no
background thread runs during tests.

Updated for Documentation/plans/2026-07-19-dynamic-department-routing-design.md's sufficiency
check: StubModelProvider's fixed placeholder text is never parseable sufficiency JSON, so a
single /chat call no longer reliably enqueues - it comes back needs_clarification for up to 2
rounds first (both rounds hit the JSON-parse-failure fallback path in orchestrator/intake.py,
since the stub ignores the prompt's round-specific instructions entirely). _send_until_queued()
resends the same message until it's actually queued, bounded at 3 attempts by the sufficiency
check's own hard cap, so these tests keep exercising the same async-queue behavior they always
did, just past that new gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

from fastapi.testclient import TestClient

import main as gateway_main

HEADERS = {"X-API-Key": "dev-only-api-key"}


def _client() -> TestClient:
    return TestClient(gateway_main.app)


def _send_until_queued(client: TestClient, message: str) -> dict:
    """Resends `message` until POST /chat returns status="queued", instead of assuming a
    fixed round count - tests in this file share one persistent dev database
    (apps/api_gateway/main.py's module-level session factory), so leftover
    clarification-round state left over from a previous test can vary. The sufficiency
    check's own 3-round cap (orchestrator/intake.py) guarantees this converges within 3
    attempts regardless of starting state."""

    body: dict = {}
    for _ in range(3):
        body = client.post("/chat", headers=HEADERS, json={"message": message}).json()
        if body.get("status") == "queued":
            return body
    return body


def test_chat_is_fire_and_forget() -> None:
    client = _client()
    body = _send_until_queued(client, "Research current market trends.")

    assert body["objective_id"].startswith("OBJ-")
    assert body["status"] == "queued"
    # The old synchronous shape is gone from this endpoint - it moved to /chat/sync.
    assert "reply" not in body
    assert "decision_id" not in body


def test_result_endpoint_reflects_full_lifecycle() -> None:
    client = _client()
    objective_id = _send_until_queued(client, "Research current market trends.")["objective_id"]

    queued = client.get(f"/objectives/{objective_id}/result", headers=HEADERS)
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert queued.json()["result"] is None

    cycle = gateway_main.drain_queue_once()
    assert objective_id in cycle.claimed

    settled = client.get(f"/objectives/{objective_id}/result", headers=HEADERS)
    assert settled.status_code == 200
    body = settled.json()
    assert body["status"] in {"completed", "failed"}
    assert body["started_at"] is not None
    assert body["completed_at"] is not None


def test_result_endpoint_requires_api_key() -> None:
    response = _client().get("/objectives/OBJ-doesnotexist/result")
    assert response.status_code == 401


def test_result_endpoint_404s_on_unknown_id() -> None:
    response = _client().get("/objectives/OBJ-doesnotexist/result", headers=HEADERS)
    assert response.status_code == 404


def test_chat_history_shows_reply_after_worker_processes_it() -> None:
    client = _client()
    objective_id = _send_until_queued(client, "Research quantum computing basics.")["objective_id"]

    gateway_main.drain_queue_once()

    result = client.get(f"/objectives/{objective_id}/result", headers=HEADERS).json()
    assert result["status"] == "completed"
    reply = result["result"]["reply"]

    history = client.get("/chat", headers=HEADERS).json()
    assert history["messages"][-1]["role"] == "coo"
    assert history["messages"][-1]["content"] == reply


def test_no_matching_department_completes_not_fails() -> None:
    """The pre-Phase-B synchronous /chat treated NoMatchingDepartmentError as a normal
    reply, not an HTTP error - the async path must preserve that (see
    dashboard_api._run_objective_and_format_reply's docstring).

    Note: by the time this reaches round 3, the consolidated objective text
    (orchestrator/intake.py + dashboard_api._consolidate_intake_conversation) includes the
    COO's own fallback clarifying-question text alongside "xyz qqq zzz" three times. If this
    assertion ever starts failing because the consolidated text accidentally overlaps some
    department's keywords, that's a real signal worth investigating (KeywordDepartmentClassifier
    is unchanged, keyword-overlap based) - don't just swap in a different nonsense string
    without checking why first."""

    client = _client()
    # Same input test_api_gateway_objectives.py uses for /objectives' 400 case - department
    # matching is keyword-based, so this needs to be an exact known non-match, not just
    # gibberish (a generic message can still route broadly across every department).
    objective_id = _send_until_queued(client, "xyz qqq zzz")["objective_id"]

    gateway_main.drain_queue_once()

    result = client.get(f"/objectives/{objective_id}/result", headers=HEADERS).json()
    assert result["status"] == "completed"
    assert "No department matched" in result["result"]["reply"]
    assert result["result"]["decision_id"] is None


def test_activity_shows_in_flight_objective_before_draining() -> None:
    client = _client()
    objective_id = _send_until_queued(client, "Research current market trends.")["objective_id"]

    activity = client.get("/activity", headers=HEADERS).json()
    in_flight_ids = {o["id"] for o in activity["in_flight_objectives"]}
    assert objective_id in in_flight_ids

    gateway_main.drain_queue_once()

    activity_after = client.get("/activity", headers=HEADERS).json()
    in_flight_ids_after = {o["id"] for o in activity_after["in_flight_objectives"]}
    assert objective_id not in in_flight_ids_after
```

Run: `./.venv/Scripts/python.exe -m pytest Tests/integration/test_api_gateway_async.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `./.venv/Scripts/python.exe -m pytest Tests/ -q`
Expected: all passing. Also check `Tests/integration/test_api_gateway_dashboard.py` and any
test in `Tests/acceptance/test_mvs_acceptance.py` that posts to `/chat` (not `/chat/sync`) -
`grep -rn '"/chat"' Tests/` to find every call site; anything not already fixed above that
asserts on the old immediate-enqueue shape needs the same `_send_until_queued` treatment or a
switch to `/chat/sync`, whichever matches what that specific test is actually trying to prove.

- [ ] **Step 7: Commit**

```bash
git add apps/api_gateway/dashboard_api.py Tests/integration/test_api_gateway_async.py
git commit -m "Wire sufficiency check into POST /chat

Round 1/2 ask the COO before enqueueing; round 3 forces proceed with the
consolidated conversation. Insufficient responses now return
{status: needs_clarification, reply} instead of {objective_id, status}.
A sufficiency-check infrastructure failure surfaces as a distinct 502,
not silently folded into either verdict. Per Documentation/plans/
2026-07-19-dynamic-department-routing-design.md Section 3.2."
```

---

### Task 7: Frontend - handle `needs_clarification` in `CooChat.jsx`

**Files:**
- Modify: `apps/web_interface/src/components/CooChat.jsx:57-89`

**Interfaces:**
- Consumes: `api.chatSend(text, filePath)` - now resolves to either `{objective_id, status: "queued"}` or `{status: "needs_clarification", reply}`.

No backend test framework covers this - it's verified by rebuilding the frontend and
exercising it in the browser with the gateway and queue worker running as separate
processes, same as `SDK_MIGRATION_PLAN.md` Phase B's verification.

- [ ] **Step 1: Update `send()`**

Replace `send()` (currently lines 57-89) in `apps/web_interface/src/components/CooChat.jsx`:

```jsx
  const send = async () => {
    if (busy || (!text.trim() && !attachment)) return;
    setBusy(true);
    setError(null);
    try {
      let filePath = null;
      if (attachment) {
        const b64 = await readFileAsBase64(attachment.file);
        const saved = await api.uploadFile(attachment.name, b64);
        filePath = saved.path;
      }
      const response = await api.chatSend(text.trim(), filePath);
      setText("");
      setAttachment(null);
      await load(); // shows the user's own message immediately either way

      // Documentation/plans/2026-07-19-dynamic-department-routing-design.md: the COO may
      // come back needing more detail instead of an objective_id - its reply is already in
      // the transcript load() just fetched, so there's nothing to poll.
      if (response.status === "needs_clarification") {
        onActivityRefresh?.();
        return;
      }

      const objectiveId = response.objective_id;
      for (let attempt = 0; attempt < RESULT_POLL_MAX_ATTEMPTS; attempt++) {
        await sleep(RESULT_POLL_INTERVAL_MS);
        const result = await api.objectiveResult(objectiveId);
        if (result.status === "completed" || result.status === "failed") break;
      }
      // Reload either way: on settlement the reply is there; on timeout this at least
      // shows nothing-new rather than leaving "Working on it…" up after busy clears - the
      // dashboard's own periodic /activity refresh, or reopening chat, will pick up a reply
      // that arrives after this window.
      await load();
      onActivityRefresh?.();
    } catch (e) {
      setError(`Could not deliver that: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  };
```

- [ ] **Step 2: Rebuild the frontend bundle**

Run: `cd apps/web_interface && npm run build`
Expected: builds cleanly, `dist/` updated.

- [ ] **Step 3: Verify in-browser**

1. Ensure the stale dev database is gone (Task 5 already did this, but confirm):
   `rm -f apps/api_gateway/api_gateway_dev.sqlite3`
2. Start the gateway (`preview_start` with the `gateway` launch config, or
   `./.venv/Scripts/python.exe Scripts/run_gateway.py`).
3. Start the queue worker in the background: `./.venv/Scripts/python.exe Scripts/run_queue_worker.py`
4. Navigate to `http://localhost:8000/ui/`, open COO chat, send a deliberately vague message
   (e.g. "help me with something"). Confirm the reply is a clarifying question and the input
   box is immediately usable again (not stuck on "Working on it…").
5. Reply again vaguely (round 2) - confirm the reply changes character (offers to proceed
   vs. asks for detail) rather than repeating the same generic question.
6. Reply a third time - confirm this one enqueues (check `GET /activity`'s
   `in_flight_objectives`, or watch the queue worker's terminal output process it), and that
   the eventual "coo" reply appears in the transcript once the worker finishes.
7. Stop the queue worker process (`TaskStop` or Ctrl+C) once verification is done.

- [ ] **Step 4: Commit**

```bash
git add apps/web_interface/src/components/CooChat.jsx apps/web_interface/dist
git commit -m "Handle needs_clarification response in CooChat.jsx

send() now branches on POST /chat's response status - skips the result-
polling loop entirely when the COO asks a clarifying question instead of
enqueueing. Verified in-browser: gateway + queue worker as separate
processes, a 3-round clarification exchange, then a completed reply. Per
Documentation/plans/2026-07-19-dynamic-department-routing-design.md."
```

---

### Task 8: Documentation update and final regression pass

**Files:**
- Modify: `Documentation/operations/technology_decisions.md`
- Modify: `Documentation/plans/2026-07-19-dynamic-department-routing-design.md` (status line only)

- [ ] **Step 1: Update `Documentation/operations/technology_decisions.md`**

Add a new section (append to the end of the file, after "## Project layout"):

```markdown
## Department classification and COO sufficiency check (2026-07-19 design doc)

`orchestrator/planner.py`'s keyword-overlap department matcher is gone - relocated behind a
swappable `DepartmentClassifier` interface (`orchestrator/classification.py`), exactly
parallel to `shared/model_gateway.py`'s `ModelProvider` pattern. `KeywordDepartmentClassifier`
(the exact old logic, unchanged) is still the dev/test default; `LLMDepartmentClassifier`
(real Claude-backed routing) is selected via `DEPARTMENT_CLASSIFIER=llm`, mirroring
`MODEL_PROVIDER`. `COOOrchestrator.receive_objective()` now makes exactly one classification
call per objective (previously two redundant keyword-matching calls - harmless when free,
wasteful once real).

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
```

- [ ] **Step 2: Update the design doc's status line**

In `Documentation/plans/2026-07-19-dynamic-department-routing-design.md`, change:

```markdown
**Status:** Approved design, not yet implemented.
```

to:

```markdown
**Status:** Implemented. See Documentation/plans/
2026-07-19-dynamic-department-routing-implementation-plan.md for the task-by-task build log
(commit history from this plan's Task 1 through Task 8).
```

- [ ] **Step 3: Run the complete test suite one final time**

Run: `./.venv/Scripts/python.exe -m pytest Tests/ -q`
Expected: all passing, 0 failures.

- [ ] **Step 4: Commit**

```bash
git add Documentation/operations/technology_decisions.md \
        Documentation/plans/2026-07-19-dynamic-department-routing-design.md
git commit -m "Document the department classifier and sufficiency check in technology_decisions.md

Marks the 2026-07-19 design doc implemented and records the final shape
(KeywordDepartmentClassifier/LLMDepartmentClassifier, the 3-round
sufficiency cap) in the running technology-decisions log, matching this
codebase's established documentation convention."
```
