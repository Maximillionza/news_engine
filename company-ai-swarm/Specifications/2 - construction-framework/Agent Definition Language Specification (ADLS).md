# `The Company AI Swarm Construction Framework`

# Agent Definition Language Specification (ADLS)

Version 1.1 — merged with Volume XIX (Enterprise Agent Development & Lifecycle Engineering
Specification, EADLES) during the repository-documents reconciliation pass. EADLES's agent
lifecycle (9-stage: Concept→Design→Development→Validation→Certification→Deployment→
Operation→Improvement→Retirement) was judged redundant with this document's own 6-stage
lifecycle (§17) and was not imported — the 9-stage version can be read as a more granular
breakdown of this document's Created/Testing/Approved/Active/Improvement/Retired stages.
EADLES's certification scale, configuration layers, creation process, and generic role
templates were genuinely new and are added below (§§18-21) as a new "Agent Engineering"
section, ahead of the Agent Creation Process this document already had.


# 1. Purpose

The Agent Definition Language Specification defines the standard format used to describe every AI agent inside The Company.

ADLS enables:

- Agent creation.

- Agent deployment.

- Agent evaluation.

- Agent versioning.

- Agent evolution.

- Agent governance.


# 2. Agent Definition Philosophy

An agent is not simply a prompt.

An agent is:

```
Identity
  +
Purpose
  +
Capabilities
  +
Tools
  +
Memory
  +
Permissions
  +
Evaluation
  +
Behaviour Rules
```


# 3. Agent Architecture Model

Every agent consists of:

```
Agent Identity
        |
Mission Definition
        |
Capability Set
        |
Reasoning Configuration
        |
Tool Access
        |
Memory Access
        |
Governance Controls
        |
Performance Evaluation
```


# 4. Core Agent Schema

Every agent must contain:

```
agent:
  identity:
  mission:
  department:
  role:
  capabilities:
  knowledge:
  memory:
  tools:
  workflow_access:
  permissions:
  behaviour:
  evaluation:
  security:
  lifecycle:
```


# 5. Identity Definition

Purpose: Defines who the agent is.

Schema:

```
identity:
  id:
  name:
  version:
  created_by:
  created_date:
  status:
```

Example: `research_agent_v1`


# 6. Mission Definition

Purpose: Defines why the agent exists.

Schema:

```
mission:
  objective:
  responsibilities:
  boundaries:
  success_definition:
```

Example:

```
Objective: Generate market intelligence reports.
Responsibilities:
  - Research markets.
  - Analyse trends.
  - Produce summaries.
Boundaries:
  - Cannot approve financial decisions.
```


# 7. Department Assignment

Every agent belongs to a department.

Schema:

```
department:
  name:
  manager:
  scope:
```

Example: `Research Department`


# 8. Capability Definition

Capabilities define what an agent can do.

Schema:

```
capabilities:
  name:
  description:
  skill_level:
  dependencies:
  evaluation:
```

Example:

```
capabilities:
  - market_research
  - data_analysis
  - report_generation
```


# 9. Knowledge Configuration

Defines information access.

Schema:

```
knowledge:
  sources:
  domains:
  restrictions:
  validation_required:
```


# 10. Memory Configuration

Defines memory behaviour, using the canonical five-tier hierarchy (EMAS §5).

Schema:

```
memory:
  short_term:
  long_term:
  department_memory:
  enterprise_memory:
  retention_policy:
```


# 11. Tool Configuration

Defines external abilities.

Schema:

```
tools:
  available:
  permissions:
  execution_limits:
  approval_required:
```


# 12. Workflow Access

Defines workflows the agent may participate in.

Schema:

```
workflow_access:
  allowed:
  restricted:
  creation_permission:
```


# 13. Permission Model

Every agent requires explicit permissions.

Schema:

```
permissions:
  read:
  write:
  execute:
  approve:
  communicate:
  deploy:
```


# 14. Behaviour Definition

Defines operating rules.

Schema:

```
behaviour:
  communication_style:
  decision_style:
  risk_tolerance:
  escalation_rules:
  failure_handling:
```


# 15. Security Definition

Defines trust boundaries.

Schema:

```
security:
  identity_level:
  trust_level:
  audit_required:
  data_classification:
  restrictions:
```


# 16. Evaluation Definition

Every agent requires measurable performance.

Schema:

```
evaluation:
  metrics:
    accuracy:
    quality:
    speed:
    cost:
  human_feedback:
  improvement_targets:
```


# 17. Lifecycle Management

Agents have states:

```
Created
  ↓
Testing
  ↓
Approved
  ↓
Active
  ↓
Improvement
  ↓
Retired
```

Schema:

```
lifecycle:
  status:
  owner:
  review_date:
  replacement_strategy:
```


# 18. Agent Engineering Principles

Adopted from EADLES.

## Principle 1 — Capability Driven Creation

Agents SHALL be created to satisfy business capabilities.


## Principle 2 — Role Before Intelligence

The required role determines the agent design.

The model does not determine the role.


## Principle 3 — Test Before Trust

No agent SHALL operate without validation.


## Principle 4 — Continuous Improvement

Agents SHALL evolve based on evidence.


## Principle 5 — Replaceability

Agents SHALL be designed so they can be replaced or upgraded.


# 19. Agent Certification Tier

Adopted from EADLES. This is a capability-maturity scale — distinct from AOSS's Authority
Level (organizational rank), AOSS's Autonomy Level (execution independence), and ESTAS's
Trust Level (earned reliability). Named "Tier," not "Level," specifically to avoid
colliding with those three existing 0-5-ish scales.

```
Tier 0  Experimental
Tier 1  Limited Deployment
Tier 2  Department Approved
Tier 3  Enterprise Approved
Tier 4  Critical Capability
```


# 20. Agent Configuration Layers

Adopted from EADLES — a conceptual decomposition of the Core Agent Schema (§4) into six
layers, useful when reasoning about which part of an agent definition a given change
affects:

```
Identity Layer      — who the agent is
Role Layer          — what the agent does
Policy Layer        — what constraints apply
Capability Layer     — what skills exist
Intelligence Layer   — which models are available
Execution Layer      — which tools can be used
```


# 21. Generic Role Templates

Adopted from EADLES. These are reusable role archetypes, complementary to (not competing
with) the four concrete MVP agents defined in First Agent Template Specification (FATS) —
use these when designing agents beyond the MVP roster.

## Analyst Agent Template

Purpose: Research and evaluation.

Capabilities: Information analysis, Summarization, Evidence evaluation.


## Builder Agent Template

Purpose: Creation and implementation.

Capabilities: Development, Configuration, Testing.


## Reviewer Agent Template

Purpose: Quality assurance.

Capabilities: Validation, Risk identification, Compliance checking.


## Manager Agent Template

Purpose: Coordination.

Capabilities: Planning, Delegation, Monitoring.


# 22. Agent Creation Process

The SDK creates agents through:

```
Need Identified
  ↓
Mission Defined
  ↓
ADLS Created
  ↓
Validation
  ↓
Testing
  ↓
Deployment
  ↓
Monitoring
```


# 23. Agent Validation Rules

Before activation:

Required:

✓ Valid identity
✓ Assigned department
✓ Defined purpose
✓ Approved permissions
✓ Capability testing
✓ Security review
✓ Evaluation metrics


# 24. Agent Communication Rules

Agents communicate through:

```
Enterprise Event Bus
  +
Service Bus
  +
Workflow Engine
```

Direct uncontrolled communication is prohibited.


# 25. Agent Evolution Rules

Agents may improve:

Allowed:

✓ Better instructions
✓ Better workflows
✓ Better tools
✓ Better knowledge

Restricted:

✗ Increasing authority
✗ Removing limits
✗ Changing governance
✗ Creating uncontrolled copies


# 26. Example Agent Definition

```
agent:
  identity:
    id: research_agent_001
    name: Research Agent
    version: 1.0

  mission:
    objective: Market intelligence generation

  department:
    name: Research

  capabilities:
    - research
    - analysis
    - reporting

  tools:
    - search
    - document_processing

  memory:
    department_memory: allowed

  permissions:
    read: research_data
    write: reports

  evaluation:
    metrics:
      accuracy:
      usefulness:
      completion_time:

  security:
    trust_level: operational

  lifecycle:
    status: active
```


# 27. MVP Agent Requirements

Initial system requires:

✓ Agent schema
✓ Agent registry
✓ Agent creation workflow
✓ Agent validation
✓ Agent deployment
✓ Agent monitoring


# 28. Future Agent Capabilities

Future versions:

- AI-generated agents.

- Agent specialisation.

- Agent collaboration networks.

- Automated capability discovery.


# 29. Completion Criteria

The Agent Definition Language is complete when:

✓ Agents can be described consistently
✓ Agents can be generated automatically
✓ Permissions are enforceable
✓ Performance can be measured
✓ Evolution can be controlled
