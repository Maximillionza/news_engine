# The Company Enterprise Architecture Standard (TCEAS)

# Universal Ontology (UOL)

**Version:** 1.0.0

Imported from the repository-documents reconciliation pass as foundational, load-bearing
content — every other Tier 1/2/3 specification's object schemas should be read as
specializations of the root EnterpriseObject defined here.


# 1. Purpose

The Universal Ontology (UOL) defines the canonical object model of The Company.

Every entity defined anywhere in TCEAS SHALL inherit from this ontology.

The ontology guarantees:

- Consistent terminology

- Shared semantics

- Traceability

- Machine readability

- Version compatibility

- Enterprise-wide interoperability

No specification SHALL redefine an object already defined within the UOL.


# 2. Root Object

Every entity is an EnterpriseObject.

```
EnterpriseObject
│
├── Organization
├── Department
├── BusinessUnit
├── Team
├── Role
├── Capability
├── Agent
├── Model
├── Tool
├── Workflow
├── Project
├── Program
├── Task
├── Artifact
├── Memory
├── Decision
├── Policy
├── Event
├── Risk
├── Metric
├── Knowledge
├── Resource
└── Service
```

Every EnterpriseObject SHALL possess the following mandatory attributes.


# 3. Common Metadata Schema

Every object SHALL include:

```
ObjectID
ObjectType
Name
Description
Version
LifecycleState
Owner
CreatedDate
ModifiedDate
Status
Classification
SecurityLevel
Parent
Children
Relationships
Tags
Metadata
Checksum
```

No object may exist without an ObjectID.


# 4. Object Identity

Every object SHALL possess a globally unique identifier.

Example:

```
ENT-000001
DEP-000034
AGT-000821
CAP-001193
TSK-093111
```

Identifiers SHALL never be reused.

Deleted objects remain archived.


# 5. Lifecycle States

Every EnterpriseObject SHALL exist in one lifecycle state.

```
Draft
  ↓
Proposed
  ↓
Approved
  ↓
Active
  ↓
Deprecated
  ↓
Archived
```

Objects SHALL never skip lifecycle transitions without authorization.

This is the default lifecycle for any object type that does not have a more specific one
defined by its owning specification. Where a specification defines a more granular lifecycle
(for example, Agent — ADLS; Workflow — EWOS; Memory — EMAS; Decision — Decision Definition
Language; Policy — Policy Definition Language), that specification's lifecycle takes
precedence for that object type, and should be understood as a refinement of this six-state
default rather than a competing model.


# 6. Relationships

Objects are connected through typed relationships.

Supported relationship types include:

```
OWNS
CONTAINS
REPORTS_TO
DEPENDS_ON
USES
GENERATES
IMPLEMENTS
GOVERNS
VALIDATES
APPROVES
EXECUTES
CREATES
REQUIRES
PROVIDES
LEARNS_FROM
SUPERSEDES
REFERENCES
```

Relationships SHALL always be directional.


# 7. Ownership Model

Every object SHALL have exactly one accountable owner.

Ownership determines:

- Maintenance

- Approval authority

- Version management

- Quality responsibility

Execution responsibility MAY differ from ownership.


# 8. Classification

Objects SHALL be classified according to sensitivity.

```
Public
Internal
Confidential
Restricted
Executive
```

Classification determines access permissions.


# 9. Versioning

Every object SHALL be version controlled.

Semantic Versioning SHALL be used.

```
Major.Minor.Patch
```

Examples:

```
1.0.0
1.2.0
2.0.0
```

Major changes SHALL maintain migration guidance.


# 10. Provenance

Every object SHALL maintain provenance.

Required fields:

```
Created By
Creation Method
Source
Evidence
Approval History
Modification History
Review History
```

No organizational knowledge SHALL exist without provenance.


# 11. Canonical Object Types

## Organization

Represents a governed enterprise.

Contains Departments, Policies, Resources and Governance.


## Department

Owns Capabilities.

Maintains Standards.

Publishes Services.

Provides Expertise.


## Capability

Represents a reusable organizational competency.

Examples:

Architecture Review

Prompt Engineering

Security Assessment

Contract Analysis

Capabilities are implementation-independent.


## Agent

Represents an autonomous worker.

Agents execute Capabilities.

Agents do not own Capabilities.


## Model

Represents computational reasoning.

Models provide intelligence.

Models possess no authority.


## Tool

Represents executable external functionality.

Examples:

Search, Filesystem, Git, Database, Browser, Python, API.


## Workflow

Defines an executable process.

Contains Tasks.

Defines dependencies.

Produces Deliverables.


## Project

Represents a bounded objective.

Projects consume organizational services.

Projects own temporary knowledge.


## Task

Represents atomic work.

Tasks SHALL NOT be decomposed below executable granularity.


## Artifact

Represents outputs.

Examples:

Document, Diagram, Code, Dataset, Specification, Presentation, Report.

Every Artifact SHALL have lineage.


## Memory

Represents retrievable knowledge.

Memory SHALL always possess:

Evidence.

Confidence.

Scope.

Retention Policy.


## Decision

Represents organizational judgement.

Every Decision SHALL include:

Alternatives.

Evidence.

Confidence.

Approver.


## Event

Represents immutable history.

Events SHALL never be modified.

Corrections SHALL create new Events.


## Policy

Represents mandatory organizational behaviour.

Policies SHALL override workflows.


## Resource

Represents consumable enterprise assets.

Examples:

Models, Compute, Storage, Budget, Time, API Limits.


## Service

Represents reusable organizational functionality.

Departments expose Services.

Projects consume Services.


# 12. Enterprise Graph

Every EnterpriseObject SHALL become a node within the Enterprise Graph.

Relationships become edges.

The graph represents:

Knowledge, Dependencies, Authority, Communication, Execution, Ownership, Learning, Memory.

The Enterprise Graph becomes the Company's primary reasoning structure.


# 13. Object Contracts

Every object SHALL publish a contract.

Minimum contract:

```
Identity
Purpose
Inputs
Outputs
Interfaces
Dependencies
Constraints
Security
Quality Metrics
Lifecycle
Owner
```

Objects SHALL interact only through published contracts.


# 14. Event Sourcing

The Company SHALL be event sourced.

Objects represent current state.

Events represent history.

State SHALL always be reconstructable from Events.

No Event may be deleted.


# 15. Knowledge Graph Integration

Every object SHALL participate in the Enterprise Knowledge Graph.

The graph SHALL support:

Semantic Search, Relationship Traversal, Impact Analysis, Dependency Discovery,
Capability Mapping, Memory Retrieval, Decision Traceability, Organizational Analytics.


# 16. Object Invariants

The following SHALL always be true:

- Every object has exactly one identity.

- Every object has one owner.

- Every object has provenance.

- Every object has lifecycle state.

- Every object has relationships.

- Every object is version controlled.

- Every object is traceable.

- Every object is discoverable.

- Every object is auditable.

- Every object is governed.

Violation of an invariant SHALL be treated as an architectural fault.


# 17. Architectural Philosophy

The Company is not a hierarchy of prompts.

It is a graph of governed enterprise objects.

Departments, Agents, Tasks, Projects, Knowledge, Decisions and Models are merely different object types operating within a shared ontology.

This ontology forms the semantic foundation upon which every subsequent specification is built.
