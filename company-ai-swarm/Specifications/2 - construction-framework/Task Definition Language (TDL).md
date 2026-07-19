# The Company Enterprise Architecture Standard (TCEAS)

# Volume III-A

# Task Definition Language (TDL)

Version 1.0.0

Imported from the repository-documents reconciliation pass — genuinely new content. Task
structure elsewhere in Specifications/ was only lightly covered (EWOS §10-11 "Task
Decomposition"/"Task Definition"; RCS §9 "Agent Task Lifecycle"); this document is more
elaborated and is now the canonical Task specification. Its Task Lifecycle (§6) is the
lifecycle referenced as canonical for the Task object type in Enterprise Implementation
Blueprint (EIB) §7 and Universal Ontology §5.


# 1. Purpose

The Task Definition Language (TDL) defines the canonical representation, lifecycle, governance, execution model, and evaluation criteria for all work performed by The Company.

A Task is the smallest governed unit of enterprise execution.

Every Project SHALL decompose into one or more Tasks.

No Agent SHALL execute work outside the context of a Task.


# 2. Definition

A Task is an Enterprise Object (Universal Ontology §2-3) representing a bounded objective with measurable completion criteria.

A Task SHALL define:

- Objective

- Inputs

- Outputs

- Constraints

- Dependencies

- Required Capabilities

- Acceptance Criteria

Tasks SHALL be atomic.

If a Task cannot be completed by a single execution team, it SHALL be decomposed into Subtasks.


# 3. Task Hierarchy

```
Program
│
Project
│
Epic
│
Workflow
│
Task
│
Subtask
│
Action
```

Only **Tasks** and **Subtasks** are executable.

Programs, Projects, Epics, and Workflows are planning constructs.


# 4. Task Schema

Every Task SHALL contain:

```
TaskID
ProjectID
WorkflowID
Title
Objective
Business Value
Priority
Complexity
Risk
Estimated Effort
Deadline
Owner
Assigned Team
Assigned Agents
Required Capabilities
Required Services
Required Models
Dependencies
Inputs
Outputs
Acceptance Criteria
Status
Confidence
Evidence
Quality Gates
Audit Trail
```


# 5. Task Types

The Company recognizes the following canonical Task categories.

## Analysis

Examples: Research, Requirements, Gap Analysis, Impact Analysis.


## Planning

Examples: Architecture, Roadmaps, Execution Plans, Schedules.


## Creation

Examples: Software, Documentation, Reports, Specifications, Presentations.


## Validation

Examples: Testing, Compliance, Peer Review, Security Review, Fact Checking.


## Decision

Examples: Architecture Approval, Risk Acceptance, Strategy Selection, Executive Approval.


## Operational

Examples: Deployment, Migration, Monitoring, Incident Response.


## Knowledge

Examples: Documentation, Knowledge Capture, Lessons Learned, Template Creation.


# 6. Task Lifecycle (canonical)

Every Task SHALL exist in exactly one runtime state.

```
Created
  ↓
Triaged
  ↓
Planned
  ↓
Assigned
  ↓
Executing
  ↓
Review
  ↓
Approved
  ↓
Completed
  ↓
Archived
```

Alternative transitions: Blocked, Waiting, Escalated, Cancelled, Rejected.


# 7. Task Complexity Model

Every Task SHALL receive a complexity score.

```
Level 1  Routine            — Minimal reasoning, Low uncertainty
Level 2  Standard           — Some reasoning, Moderate uncertainty
Level 3  Advanced           — High reasoning, Multiple dependencies
Level 4  Expert             — Cross-domain, High risk, Strategic
Level 5  Enterprise Critical — Mission critical, Executive oversight, Multiple review cycles
```

Complexity SHALL determine: Model allocation, Agent selection, Review requirements, Quality
gates.

Note: this is a 5-level Task Complexity scale, distinct from Resource Definition Language
(RDL) §8's 4-level Reasoning Tier scale (a model-capability classification, not a task
classification). No numeric mapping between the two is defined anywhere in the corpus; RDL
§10's Intelligence Allocation Matrix gives worked examples of typical pairings, and the COO
retains override authority per RDL §10.


# 8. Task Risk Model

Each Task SHALL receive independent risk scores across: Technical, Operational, Legal,
Compliance, Security, Financial, Reputational, and an Overall Risk rating.

High-risk Tasks SHALL require additional review.


# 9. Capability Requirements

Tasks request Capabilities. Never Departments.

Example:

```
Task: Design Authentication System
Required Capabilities: Security Architecture, Identity Management, Threat Modeling,
                        API Design, Documentation
```

The COO SHALL determine which Agents satisfy those Capabilities.


# 10. Task Inputs

Inputs SHALL define: Required Knowledge, Artifacts, Policies, Evidence, External Data,
Dependencies.

Tasks SHALL reject incomplete inputs.


# 11. Task Outputs

Outputs SHALL include: Deliverables, Evidence, Confidence, Metrics, Recommendations, Open
Questions, Knowledge Contributions.

Every output SHALL identify its originating Task.


# 12. Task Contracts

Every Task SHALL publish a contract.

```
Objective
Scope
Required Capabilities
Inputs
Outputs
Quality Criteria
Acceptance Criteria
Security Classification
Dependencies
Escalation Rules
Completion Definition
```

No Task SHALL execute without a valid contract.


# 13. Acceptance Criteria

Tasks SHALL define measurable completion.

Examples: Code Compiles, Tests Pass, Compliance Verified, Architecture Approved,
Documentation Complete, Peer Review Passed.

Acceptance SHALL never rely upon subjective judgement alone.


# 14. Evidence Model

Every completed Task SHALL provide evidence, including: Supporting Artifacts, Source
References, Validation Results, Quality Reports, Review Records, Confidence Assessment.

Evidence SHALL remain permanently traceable.


# 15. Task Scheduling

The COO SHALL schedule Tasks according to: Priority, Risk, Dependencies, Available Capacity,
Capability Availability, Deadlines, Estimated Cost.

Scheduling SHALL optimize enterprise objectives rather than local optimization.


# 16. Parallel Execution

Tasks MAY execute simultaneously when: Dependencies are satisfied, Required resources are
available, No shared mutable state exists.

Parallel execution SHALL be preferred where beneficial.


# 17. Task Review (risk-proportional)

Completed Tasks SHALL undergo review proportional to risk.

```
Routine    → Self-validation
Standard   → Peer review
Advanced   → Department review
Critical   → Independent review + Executive approval
```


# 18. Escalation

A Task SHALL escalate whenever: Confidence falls below threshold, Evidence conflicts,
Dependencies fail, Resources become unavailable, Risk increases, Acceptance criteria cannot
be achieved.

Escalation SHALL follow the organizational hierarchy.


# 19. Metrics

Every Task SHALL publish: Completion Time, Review Count, Rework Count, Confidence, Resource
Usage, Cost, Quality Score, Automation Percentage, Knowledge Contribution, Reuse Percentage.

These metrics SHALL contribute to enterprise analytics.


# 20. Task Invariants

The following SHALL always be true:

- Every Task has one objective.

- Every Task has one owner.

- Every Task has measurable completion.

- Every Task produces traceable outputs.

- Every Task records evidence.

- Every Task maintains an audit trail.

- Every Task is independently reviewable.

- Every Task contributes measurable value.

Violation of an invariant SHALL invalidate the Task.


# 21. Design Philosophy

The Task is the fundamental execution object of The Company.

Projects organize Tasks.

Workflows coordinate Tasks.

Agents execute Tasks.

Capabilities enable Tasks.

Models reason about Tasks.

Memory supports Tasks.

Policies govern Tasks.

Quality validates Tasks.

The Enterprise exists to complete Tasks with maximum effectiveness, transparency, and accountability.
