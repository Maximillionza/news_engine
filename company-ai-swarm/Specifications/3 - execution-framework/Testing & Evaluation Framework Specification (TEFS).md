# The Company AI Swarm Construction Framework

# Testing & Evaluation Framework Specification (TEFS)

Version 1.0

Imported from the repository-documents reconciliation pass — genuinely new content. Neither
MVS nor any other Tier 3 document defines an evaluation/testing framework; this fills that
gap. Note: every "evaluation model" below is a metric-name schema, not a scored rubric — no
numeric thresholds, pass/fail cutoffs, or test fixtures are defined anywhere in the source
corpus. Treat §18's MVP Acceptance Tests as narrative Input/Expected pairs to be made
concrete (with real fixture data and thresholds) during implementation, not as ready-to-run
tests.


# 1. Purpose

The Testing & Evaluation Framework Specification defines the validation system for The Company AI Enterprise Operating System.

The framework ensures:

- Components function correctly.

- Agents perform their intended roles.

- The COO makes appropriate decisions.

- Workflows execute reliably.

- Memory improves performance without introducing bias.

- Enterprise rules remain enforced.


# 2. Evaluation Philosophy

The Company SHALL be evaluated at five levels:

```
Component
  ↓
Agent
  ↓
Department
  ↓
Enterprise
  ↓
Evolution
```


# 3. Testing Layers

## Layer 1 — Component Testing

Purpose: Validate individual technical components.

Applies to: Services, APIs, Databases, Runtime modules.

Examples: Memory service stores records correctly. Model gateway routes requests. Workflow
engine executes steps.


## Layer 2 — Agent Testing

Purpose: Validate individual agent behaviour.

Tests: Role adherence, Capability execution, Tool usage, Output quality, Permission
compliance.


## Layer 3 — Workflow Testing

Purpose: Validate multi-agent collaboration.

Tests: Task handoff, Department coordination, Failure recovery, Review cycles.


## Layer 4 — Enterprise Testing

Purpose: Validate The Company as a whole.

Tests: Objective completion, Governance compliance, Resource allocation, Decision quality.


## Layer 5 — Evolution Testing

Purpose: Validate learning and improvement.

Tests: Memory usefulness, Knowledge accuracy, Process improvement, Regression prevention.


# 4. Agent Evaluation Model

Every agent SHALL be evaluated using:

```
agent_evaluation:
  identity_alignment:
  capability_accuracy:
  task_completion:
  reasoning_quality:
  tool_usage:
  memory_usage:
  output_quality:
  governance_compliance:
```


# 5. Agent Performance Metrics

## Accuracy

Did the agent produce correct outputs?


## Reliability

Does it perform consistently?


## Efficiency

Did it use appropriate resources?


## Governance

Did it follow permissions and boundaries?


## Improvement

Did performance improve over time?


# 6. COO Evaluation Framework

The COO is evaluated separately because it controls operations.


## Task Analysis Quality

Measures: Correct decomposition, Appropriate complexity scoring, Requirement understanding.


## Allocation Quality

Measures: Correct department selection, Appropriate agent selection, Appropriate model
selection.


## Resource Efficiency

Measures: Cost, Speed, Model utilisation.


## Outcome Quality

Measures: Objective achievement, User satisfaction, Review results.


# 7. COO Decision Evaluation Record

Every significant COO decision SHALL generate:

```
coo_decision_evaluation:
  decision:
  reasoning:
  available_options:
  selected_option:
  expected_result:
  actual_result:
  accuracy:
  lesson:
```

This is the evaluation counterpart to the COO Decision Record (COOS §22) — the Decision
Record captures what was decided; this record captures how well the decision performed
against its expectation.


# 8. Workflow Evaluation

Every workflow SHALL measure:

```
workflow_evaluation:
  completion_rate:
  execution_time:
  failures:
  retries:
  agent_performance:
  quality_score:
```


# 9. Memory Evaluation

Memory must improve performance without creating bias.


## Memory Usefulness Test

Question: Did memory improve the current decision?


## Memory Bias Test

Question: Did memory cause an incorrect assumption?

Example:

Invalid: "Previous project failed compliance review. Current project automatically
classified as risky."

Valid: "Previous project identified a compliance category requiring review."


# 10. Knowledge Evaluation

Knowledge records require:

```
knowledge_evaluation:
  source_quality:
  validation_status:
  confidence:
  usage_frequency:
  accuracy_history:
```


# 11. Model Evaluation Framework

Models are evaluated independently.

Metrics:

## Capability

Can the model perform the required reasoning?


## Cost

Is the model economically appropriate?


## Speed

Does performance meet requirements?


## Reliability

Does output quality remain consistent?


# 12. Model Routing Improvement

The COO SHALL continuously evaluate:

```
Task Requirements
  ↓
Chosen Model
  ↓
Actual Result
  ↓
Routing Improvement
```


# 13. Testing Environments

The Company SHALL maintain:


## Development Environment

Purpose: Building new capabilities.


## Testing Environment

Purpose: Validation before deployment.


## Production Environment

Purpose: Live operation.


## Simulation Environment

Purpose: Future enterprise experiments (see Enterprise Simulation & Digital Twin
Specification).


# 14. Regression Testing

Before introducing changes:

The system SHALL verify: Existing agents still operate, Existing workflows still function,
Governance rules remain intact, Memory behaviour remains correct.


# 15. Architecture Compliance Testing

The system SHALL verify:

```
Director
  ↓
COO
  ↓
Departments
  ↓
Agents
```

Rules remain enforced.

Tests include: Can agents bypass COO? Can memory override policy? Can departments exceed
permissions? Can models be selected incorrectly?


# 16. Security Testing

Validate: Access permissions, Data boundaries, Agent privileges, Tool restrictions, Audit
logging.


# 17. Human Oversight Testing

The Company SHALL support: Human review, Human override, Human approval workflows, Decision
inspection.


# 18. MVP Acceptance Tests

The MVP passes when:


## Test 1 — Objective Execution

Input: A business objective.

Expected: The Company creates and completes an execution plan.


## Test 2 — Agent Collaboration

Expected: Multiple agents collaborate through the COO.


## Test 3 — Model Routing

Expected: Different tasks receive appropriate models.


## Test 4 — Memory Behaviour

Expected: Previous experience improves decisions without creating assumptions.


## Test 5 — Review Loop

Expected: Completed work is evaluated and improved.

These five tests are complementary to, not a replacement for, the MVP Validation
Specification (MVS)'s ten formal test categories — treat these as the qualitative behaviours
MVS's tests should demonstrate.


# 19. Continuous Improvement Loop

The Company SHALL operate:

```
Execute
  ↓
Measure
  ↓
Evaluate
  ↓
Identify Improvement
  ↓
Implement Change
  ↓
Validate
  ↓
Repeat
```


# 20. Evaluation Storage

Evaluation results SHALL be stored as:

```
evaluation_record:
  subject:
  type:
  metrics:
  result:
  recommendations:
  timestamp:
```


# 21. Completion Criteria

The evaluation framework is complete when:

✓ Agents can be tested
✓ COO decisions can be evaluated
✓ Workflows can be measured
✓ Memory impact can be assessed
✓ Model selection can improve
✓ Enterprise behaviour can be validated
