# The Company Enterprise Architecture Standard (TCEAS)

# Volume XXIX

# Enterprise Data Model Specification (EDMS)

Version 1.1

Imported from the repository-documents reconciliation pass. This is the document TAS
(Technical Architecture Specification) explicitly deferred to at its close ("This is the
point where the architecture becomes database and object design") and which the original
gap analysis of this repository flagged as the single largest blocking gap — every prior
schema in the corpus was a bare field-name list with no concrete entity catalogue tying them
together. This document is that catalogue. Reconciliation note: §15's Memory Types listed a
sixth memory-tier variant ("Strategic Memory" in place of "Historical Memory," otherwise
matching EMAS's five tiers almost exactly). Corrected below to use EMAS's canonical five
tiers exactly (Working, Project, Department, Enterprise, Historical) — this document's
"Strategic Memory" concept is preserved as a note under Enterprise Memory, consistent with
the same correction already made in EDIS §12.


# 1. Purpose

The Enterprise Data Model Specification defines the canonical data structures required for The Company AI Enterprise Operating System.

EDMS governs:

- Enterprise entities.

- Data schemas.

- Relationships.

- Identity models.

- Memory structures.

- Knowledge structures.

- Operational records.

- Performance records.


# 2. Data Architecture Philosophy

The Company SHALL treat data as enterprise knowledge infrastructure.

Data SHALL provide:

```
Identity
Context
Relationships
History
Decision Support
Learning Capability
```


# 3. Enterprise Data Model Overview

The Company data architecture consists of:

```
                 Enterprise Data Model

                         |

 ------------------------------------------------

 |          |           |           |           |

People    Org        Work        Knowledge   Intelligence

Objects   Objects    Objects     Objects     Objects

 |          |           |           |           |

 ------------------------------------------------

                         |

                  Performance Data

                         |

                  Audit History
```


# 4. Core Enterprise Entities

The Company SHALL define the following primary entities:

1. Enterprise Entity

2. Department Entity

3. Agent Entity

4. Human Entity

5. Task Entity

6. Workflow Entity

7. Project Entity

8. Capability Entity

9. Knowledge Entity

10. Memory Entity

11. Decision Entity

12. Event Entity

13. Performance Entity

Every entity below is a specialization of the root EnterpriseObject defined in Universal
Ontology §2-3; fields shown here are in addition to UOL's common metadata schema (ObjectID,
ObjectType, Name, Version, LifecycleState, Owner, CreatedDate, ModifiedDate, Classification,
Relationships, etc.) unless a field name obviously duplicates one already in that schema.


# 5. Enterprise Entity Schema

Represents The Company itself.

```
Enterprise_ID
Name
Purpose
Mission
Values
Operating Principles
Governance Rules
Created_Date
Version
Status
```


# 6. Department Entity Schema

Represents organizational capability units.

Example: Research Department, Engineering Department, Compliance Department.

Schema:

```
Department_ID
Department_Name
Mission
Purpose
Capabilities
Authority_Level
Parent_Department
Assigned_Agents
Performance_Metrics
Status
```

Relationships:

```
Department HAS Agents
Department PROVIDES Capabilities
```


# 7. Agent Entity Schema

Represents an AI employee.

Schema:

```
Agent_ID
Agent_Name
Role
Department_ID
Purpose
Capabilities
Instructions
Model_Profile
Tool_Access
Memory_Access
Permissions
Performance_Profile
Creation_Date
Version
Status
```


# 8. Agent Capability Model

Agents SHALL have explicit capabilities.

Example:

```
Agent: Compliance Analyst
Capabilities: Regulatory Analysis, Risk Identification, Policy Review, Audit Preparation
```

Capability schema:

```
Capability_ID
Name
Description
Category
Complexity_Level
Required_Authority
Validation_Status
```


# 9. Human Entity Schema

Represents human collaborators.

```
Human_ID
Name
Role
Department
Permissions
Responsibilities
Approval_Authority
Interaction_History
```


# 10. Task Entity Schema

Represents work entering The Company. This is the storage-layer counterpart to the fuller
Task Schema in Task Definition Language (TDL) §4 — TDL's schema is authoritative for what a
Task must contain; this entity is the persisted-record subset.

```
Task_ID
Objective
Description
Requester
Complexity
Risk_Level
Required_Capabilities
Assigned_Department
Assigned_Agents
Priority
Status
Created_Date
Completed_Date
```


# 11. Task Classification Model

Every task SHALL contain: Complexity, Risk, Urgency, Domain, Required Intelligence Level,
Required Review Level.

Examples:

```
Task: Draft customer email        → Complexity: Low  → Model: Basic reasoning     → Review: Automated
Task: Design regulatory strategy  → Complexity: High → Model: Advanced reasoning  → Review: Human approval
```


# 12. Workflow Entity Schema

Represents coordinated execution.

```
Workflow_ID
Name
Purpose
Steps
Dependencies
Assigned_Agents
Approval_Points
Execution_Status
Outcome
```

Relationship: `Task CREATES Workflow`


# 13. Project Entity Schema

Represents longer-term initiatives.

```
Project_ID
Name
Objective
Stakeholders
Tasks
Departments
Resources
Timeline
Risk_Profile
Outcome
```


# 14. Memory Entity Schema

Critical for institutional intelligence.

Memory SHALL NOT simply store information. It SHALL store contextual knowledge.

Schema:

```
Memory_ID
Memory_Type
Information
Context
Source
Confidence
Applicability
Created_Date
Last_Validated
Expiry_Date
Validation_Status
```


# 15. Memory Types (canonical — EMAS five-tier)

The Company SHALL maintain the five canonical memory tiers (EMAS §5):

## Working Memory

Temporary execution context.


## Project Memory

Specific project knowledge, isolated to that project.


## Department Memory

Capability knowledge.


## Enterprise Memory

Validated organizational knowledge. Executive-level ("strategic") patterns are stored here
as a scoped view — not as a separate tier — consistent with the same correction made in
EDIS §12.


## Historical Memory

Archived organizational history. Does not automatically influence active reasoning.


# 16. Context Boundary Model

Every memory SHALL contain applicability rules.

Example:

Incorrect — stored as an overgeneralization:

```
Previous Project: Healthcare data failed compliance review
Stored as: "All data projects are risky"
```

Correct — stored with explicit context:

```
Healthcare project
Jurisdiction: South Africa
Data Type: Medical records
Risk: High
Applicable Controls: POPIA healthcare requirements
```


# 17. Knowledge Entity Schema

Represents enterprise understanding.

```
Knowledge_ID
Entity_Type
Name
Description
Relationships
Source
Confidence
Validation_Status
Last_Updated
```


# 18. Knowledge Graph Model

Relationships:

```
ENTITY -- RELATIONSHIP -- ENTITY
```

Example:

```
Customer Data REQUIRES Privacy Controls GOVERNED_BY POPIA
```


# 19. Decision Entity Schema

Stores important decisions. This is the storage-layer counterpart to the fuller Decision
Object in Decision Definition Language (DDL) §5.

```
Decision_ID
Decision
Reasoning
Inputs
Participants
Approvals
Date
Outcome
Review_Date
```


# 20. Event Entity Schema

Represents enterprise activity.

```
Event_ID
Event_Type
Actor
Timestamp
Object
Action
Result
```

Examples: `AgentCreated`, `TaskCompleted`, `WorkflowFailed`, `MemoryUpdated`, `PolicyChanged`.


# 21. Performance Entity Schema

Stores measurement information.

```
Performance_ID
Entity
Metric
Value
Time_Period
Benchmark
Trend
Assessment
```


# 22. Relationship Model

Core relationships:

```
Enterprise HAS Departments
Department HAS Agents
Agent PERFORMS Tasks
Task EXECUTES Workflow
Workflow CREATES Events
Agent CREATES Memory
Knowledge INFORMS Decision
```


# 23. Data Governance Rules

All enterprise data SHALL have: Owner, Classification, Access Rules, Validation Status,
Retention Policy, Audit History.


# 24. Data Classification

The Company SHALL classify information: Public, Internal, Confidential, Restricted,
Strategic.


# 25. Data Quality Rules

Data SHALL be evaluated for: Accuracy, Completeness, Freshness, Context, Reliability.


# 26. Memory Protection Rules

The Company SHALL prevent: Context leakage, Incorrect generalization, Historical bias,
Unvalidated learning.


# 27. Agent Data Access Model

Agents SHALL access only required information.

Example:

```
Marketing Agent
CAN ACCESS: Market research
CANNOT ACCESS: Private employee records
```


# 28. Data Lifecycle

Every data object SHALL follow:

```
Created
  ↓
Validated
  ↓
Used
  ↓
Updated
  ↓
Archived
  ↓
Retired
```


# 29. Data Versioning

The Company SHALL maintain: Schema versions, Knowledge versions, Memory versions, Decision
history.


# 30. Data Invariants

The following SHALL always be true:

- Every entity has identity.

- Every decision has context.

- Every memory has applicability.

- Every agent has permissions.

- Every capability has ownership.

- Every important action is traceable.


# 31a. Recommended Storage Mapping

Adopted from the "Core Data Schema Specification (CDSS)" document, folded in here since the
rest of that document's schemas were redundant with this one, DDL, TDL, and UOL. Recommended
storage technology per entity type, consistent with EIAS §8's database architecture:

| Entity | Storage |
|---|---|
| Enterprise | PostgreSQL |
| Department | PostgreSQL |
| Agent | PostgreSQL |
| Tasks | PostgreSQL |
| Workflows | PostgreSQL |
| Memory | Vector Database + PostgreSQL |
| Knowledge | Graph Database |
| Documents | Object Storage |
| Logs | Observability Platform |


# 31. Design Philosophy

The data model is the foundation of enterprise intelligence.

Without structured identity: Agents cannot be managed.

Without relationships: Knowledge cannot emerge.

Without context: Memory becomes dangerous.

Without history: Learning becomes impossible.

The Company becomes intelligent because it can understand not only information, but the relationships and circumstances surrounding that information.
