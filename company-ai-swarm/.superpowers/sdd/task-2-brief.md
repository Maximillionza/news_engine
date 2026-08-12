### Task 2: Department Head agent registration

**Files:**
- Create: `agents/active/research_head/agent.yaml`
- Create: `agents/active/engineering_head/agent.yaml`
- Create: `agents/active/compliance_head/agent.yaml`
- Create: `agents/active/operations_head/agent.yaml`
- Modify: `departments/research/definition.yaml`
- Modify: `departments/engineering/definition.yaml`
- Modify: `departments/compliance/definition.yaml`
- Modify: `departments/operations/definition.yaml`
- Test: `Tests/unit/test_department_registry.py`

**Interfaces:**
- Consumes: `DepartmentDefinition.leader: str` (Task 1 already promoted this to a first-class
  field - do not modify `services/orchestrator/department_registry.py` in this task).
- Produces: four registered `AgentDefinition`s (`research_head_001`, `engineering_head_001`,
  `compliance_head_001`, `operations_head_001`) reachable via `AgentRegistry.get(...)`; each
  department's `leader` field set to the matching head's identity id. Task 3/4 depend on
  `department.leader` resolving to a real agent for research/engineering/compliance/operations.

- [ ] **Step 1: Write the failing tests**

Create `Tests/unit/test_department_registry.py`:

```python
"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3's Department
Head agent registration: `department.leader` promoted from department_registry.py's
catch-all `extra` dict to a first-class field, and the four dispatch-relevant departments
(research, engineering, compliance, operations) each carry a real head agent identity.
Strategy is deliberately excluded - its empty `agents` list already keeps it out of the
classifier's matches before triage would ever run.
"""

from __future__ import annotations

from pathlib import Path

from agent_runtime.registry import AgentRegistry
from orchestrator.department_registry import DepartmentRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]


def _departments() -> DepartmentRegistry:
    registry = DepartmentRegistry(REPO_ROOT / "departments")
    registry.load_all()
    return registry


def _agents() -> AgentRegistry:
    registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    registry.load_all()
    return registry


def test_leader_is_a_first_class_field_not_in_extra() -> None:
    research = _departments().get("research")

    assert research is not None
    assert research.leader == "research_head_001"
    assert "leader" not in research.extra


class TestDispatchRelevantDepartmentsHaveARegisteredHead:
    def test_research_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        research = departments.get("research")

        assert research is not None
        assert agents.get(research.leader) is not None
        assert research.leader not in research.agents

    def test_engineering_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        engineering = departments.get("engineering")

        assert engineering is not None
        assert agents.get(engineering.leader) is not None
        assert engineering.leader not in engineering.agents

    def test_compliance_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        compliance = departments.get("compliance")

        assert compliance is not None
        assert agents.get(compliance.leader) is not None
        assert compliance.leader not in compliance.agents

    def test_operations_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        operations = departments.get("operations")

        assert operations is not None
        assert agents.get(operations.leader) is not None
        assert operations.leader not in operations.agents


def test_strategy_has_no_head_by_design() -> None:
    departments, agents = _departments(), _agents()
    strategy = departments.get("strategy")

    assert strategy is not None
    assert strategy.leader == ""
    assert agents.get("strategy_head_001") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest Tests/unit/test_department_registry.py -v`
Expected: FAIL - `research.leader == ""` (not yet `"research_head_001"`), and
`agents.get(research.leader)` is `None` (no head agents registered yet). `DepartmentDefinition`
already has the `leader` field (Task 1) - this task only fails on data, not on a missing field.

- [ ] **Step 3: Set `leader` in the four dispatch-relevant `departments/*/definition.yaml` files**

In `departments/research/definition.yaml`, change `leader: ""` to `leader: research_head_001`.
In `departments/engineering/definition.yaml`, change `leader: ""` to `leader: engineering_head_001`.
In `departments/compliance/definition.yaml`, change `leader: ""` to `leader: compliance_head_001`.
In `departments/operations/definition.yaml`, change `leader: ""` to `leader: operations_head_001`.
Leave `departments/strategy/definition.yaml`'s `leader: ""` unchanged.

- [ ] **Step 4: Create `agents/active/research_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/research/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: research_head_001
    name: "Research Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Research Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require research, analysis, or reporting."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the research work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: research
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 5: Create `agents/active/engineering_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/engineering/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: engineering_head_001
    name: "Engineering Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Engineering Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require building or maintaining technical capabilities."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the engineering work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: engineering
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 6: Create `agents/active/compliance_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/compliance/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: compliance_head_001
    name: "Compliance Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Compliance Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require identifying applicable obligations or assessing risk."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the compliance work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: compliance
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 7: Create `agents/active/operations_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/operations/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: operations_head_001
    name: "Operations Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Operations Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require validating outputs or monitoring workflow execution."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the review work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: operations
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 8: Run tests to verify they pass**
Run: `python -m pytest Tests/unit/test_department_registry.py -v`
Expected: all tests PASS

- [ ] **Step 9: Run the full existing suite to confirm no regressions**
Run: `python -m pytest Tests/ -q`
Expected: all tests PASS (the four departments' `agents:` lists are unchanged, so
`KeywordDepartmentClassifier`/`allocator.select_agent()` behavior is unaffected)

- [ ] **Step 10: Commit**
```bash
git add agents/active/research_head/agent.yaml agents/active/engineering_head/agent.yaml \
  agents/active/compliance_head/agent.yaml agents/active/operations_head/agent.yaml \
  departments/research/definition.yaml departments/engineering/definition.yaml \
  departments/compliance/definition.yaml departments/operations/definition.yaml \
  Tests/unit/test_department_registry.py
git commit -m "feat: register a Department Head agent for each dispatch-relevant department"
```

---

