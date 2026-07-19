# The Company Enterprise Architecture Standard (TCEAS)

# Volume XII

# Department Operating Model Specification (DOMS)

Version 1.1 — merged with content from Volume II (Organization Definition Language, ODL)
and Volume X (Reference Architecture Specification, RAS) during the repository-documents
reconciliation pass. ODL's generic department schema and lifecycle were judged redundant
with this document's own (§5, §22-23) and were not imported; ODL's executive org chart and
15-department catalogue, and RAS's four worked department examples, were genuinely new and
are added below (§§28-30) as new closing sections. Note: RAS's worked examples use richer,
multi-agent department rosters (e.g. Engineering: Software Architect, Developer, Tester,
DevOps Engineer) that go well beyond the MVS-canonical single-agent-per-department MVP —
treat them as illustrative post-MVP expansion, not the MVP target (see FATS for the MVP
roster).


# 1. Purpose

The Department Operating Model Specification defines the structure, governance, operation, and evolution of departments within The Company.

The DOMS governs:

- Department creation.

- Department leadership.

- Capability ownership.

- Specialist agent organization.

- Department workflows.

- Department memory.

- Performance measurement.

- Cross-department collaboration.

- Department evolution.


# 2. Definition of a Department

A Department is an organizational capability domain responsible for delivering specialized enterprise outcomes.

A Department SHALL contain:

- Purpose.

- Leadership.

- Capabilities.

- Roles.

- Agents.

- Resources.

- Policies.

- Knowledge.

- Performance measures.


# 3. Department Principles

## Principle 1 — Capability First

Departments exist to provide capabilities.

They SHALL NOT exist simply to group agents.


## Principle 2 — Clear Ownership

Every capability SHALL have an accountable owner.


## Principle 3 — Collaboration Over Isolation

Departments provide expertise but operate as part of the wider enterprise.


## Principle 4 — Specialized Intelligence

Departments SHOULD develop domain-specific expertise.


## Principle 5 — Evolution Through Evidence

Departments SHALL evolve based on measurable performance and enterprise needs.


# 4. Department Architecture

```
                Department

                    │

            Department Leader

                    │

        ┌───────────┼───────────┐

        ▼           ▼           ▼

  Capabilities   Policies    Knowledge

        │

 Capability Groups

        │

 Specialist Agents

        │

 Tools + Resources
```


# 5. Department Object

Every Department SHALL contain:

```
DepartmentID
Name
Purpose
Leader
Mission
Capabilities
Roles
Agents
Resources
Policies
Memory Domain
Services Provided
Dependencies
Performance Metrics
Lifecycle State
```


# 6. Department Creation

A Department MAY be created when:

A recurring capability is required.

Existing departments cannot efficiently provide the capability.

Specialized governance is required.

Enterprise complexity exceeds current structure.


# 7. Department Creation Process

```
Capability Need Identified
  ↓
Business Case Created
  ↓
Capability Analysis
  ↓
Policy Review
  ↓
Leadership Assigned
  ↓
Resources Allocated
  ↓
Department Activated
```


# 8. Department Leadership

Every Department SHALL have a Department Leader.

The Department Leader is responsible for:

- Capability quality.

- Agent performance.

- Department strategy.

- Knowledge development.

- Resource management.

- Escalation.


# 9. Department Leader Authority

Department Leaders MAY:

Create specialist agents.

Request resources.

Define capability standards.

Approve department workflows.

Recommend policy changes.


Department Leaders SHALL NOT:

Override enterprise policy.

Change constitutional rules.

Modify other departments without authority.


# 10. Capability Model

Departments are composed of capabilities.

Example:

Engineering Department:

```
Software Development
Architecture
Testing
DevOps
Infrastructure
```

Each capability SHALL define:

Purpose.

Required expertise.

Supported tasks.

Quality criteria.

Required resources.


# 11. Capability Ownership

Every capability SHALL have:

Capability Owner.

Capability Definition.

Capability Standards.

Capability Metrics.

Capability Knowledge Base.


# 12. Specialist Agent Pools

Departments SHALL maintain agent pools.

Example:

Security Department:

```
Security Architecture Agents
Threat Analysis Agents
Compliance Agents
Incident Response Agents
```

Agent pools allow:

Dynamic allocation.

Load balancing.

Specialization.

Replacement.


# 13. Department Services

Departments SHALL expose capabilities as services.

Example:

Legal Department:

Services:

Contract Analysis.

Regulatory Research.

Privacy Assessment.

Risk Review.


Services are accessed through the Enterprise Service Bus.


# 14. Department Operating Cycle

Every Department SHALL operate through:

```
Receive Demand
  ↓
Analyze Requirement
  ↓
Allocate Capability
  ↓
Assign Agents
  ↓
Execute Work
  ↓
Review Quality
  ↓
Capture Learning
  ↓
Improve Capability
```


# 15. Department Workflow Integration

Departments SHALL participate in enterprise workflows.

A workflow MAY involve:

One department.

Multiple departments.

Temporary project departments.

Virtual teams.


# 16. Cross-Department Collaboration

Collaboration SHALL occur through:

Enterprise Service Bus.

Event Bus.

Shared workflows.

Defined contracts.


Direct uncontrolled communication SHALL be prohibited.


# 17. Virtual Departments

The Company MAY create temporary departments.

Examples:

AI Transformation Team.

Merger Analysis Unit.

Emergency Response Group.


Virtual departments SHALL have:

Purpose.

Leader.

Duration.

Capabilities.

Closure criteria.


# 18. Department Memory

Each Department SHALL maintain departmental memory (the "Department" tier of the canonical
five-tier hierarchy — see EMAS §5).

Department memory includes:

Validated practices.

Capability knowledge.

Standards.

Lessons learned.

Patterns.


Department memory SHALL NOT automatically become enterprise memory.


# 19. Department Learning

Departments SHALL learn from:

Completed tasks.

Project outcomes.

Performance metrics.

Reviews.

Failures.


Learning SHALL pass through validation before promotion.


# 20. Department Performance Metrics

Departments SHALL measure:

Capability quality.

Task success.

Response time.

Cost efficiency.

Knowledge contribution.

Agent performance.

Stakeholder satisfaction.


# 21. Department Health Score

The Company SHALL calculate Department Health.

Factors:

Capability demand.

Performance.

Resource utilization.

Quality.

Innovation.

Risk.


# 22. Department Evolution

Departments MAY:

Expand.

Merge.

Split.

Retire.

Create new capabilities.

Remove obsolete capabilities.


Changes require:

Impact assessment.

Resource analysis.

Governance review.


# 23. Department Retirement

A Department MAY be retired when:

Capability demand disappears.

Capability moves elsewhere.

Performance is consistently poor.

Technology replaces capability.


Retirement SHALL preserve:

Historical records.

Knowledge.

Decision history.

Lessons learned.


# 24. Department Security

Departments SHALL have:

Access boundaries.

Data restrictions.

Tool permissions.

Memory permissions.

Agent permissions.


# 25. Department Metrics

Enterprise leadership SHALL monitor:

Number of active capabilities.

Capability maturity.

Agent utilization.

Task throughput.

Quality scores.

Innovation rate.


# 26. Department Invariants

The following SHALL always be true:

- Every department has a purpose.

- Every department has ownership.

- Every department provides capabilities.

- Every capability has an owner.

- Every agent belongs to a capability.

- Every capability has standards.

- Every department is measurable.

- Every department can evolve.

- No department operates outside governance.

- No department creates uncontrolled knowledge.


# 27. Executive Layer Above Departments

Adopted from ODL. Departments sit beneath an executive governance structure:

```
Board of Directors
        │
        ▼
Director (CEO)
        │
        ▼
Chief Operating Officer (COO)
        │
        ▼
Enterprise Management Office
        │
        ├─────────────┬──────────────┬──────────────┐
        ▼             ▼              ▼              ▼
Departments      Shared Services   Governance   Innovation
```

Authority SHALL always flow downward. Accountability SHALL always flow upward.

The Enterprise Management Office (EMO) supports executive operations and MAY contain, as
sub-offices: Project Management Office, Human Resources, Enterprise Knowledge Office,
Internal Audit, Risk Office, Financial Operations, Resource Operations. These sub-offices
are not part of the MVS-canonical MVP — their responsibilities are covered by the MVP's
Governance Layer (Security, Audit, Monitoring) and COO until enterprise scale justifies
splitting them out.


# 28. Standard Department Catalogue

Adopted from ODL. The MVS-canonical MVP requires exactly four departments (Research,
Engineering, Compliance, Operations — see MVS §3, FATS §8). At enterprise scale, The Company
MAY grow toward this fuller catalogue; each entry names what the department owns:

```
Executive Office        — Enterprise governance, executive decision making, strategic planning
Operations              — Execution, scheduling, coordination, monitoring, workflow optimization
Project Management      — Projects, roadmaps, planning, milestones, reporting
Enterprise Architecture — System design, technology strategy, reference/solution architecture
Engineering             — Implementation, software, infrastructure, automation, testing, deployment
Research & Intelligence — Fact finding, analysis, competitive intelligence, validation
Data & AI               — Machine learning, LLM systems, RAG, knowledge graphs, evaluation
Security                — Cybersecurity, threat modelling, identity, access control, cryptography
Legal & Compliance      — Regulations, privacy, licensing, governance, contract analysis
Quality Assurance       — Verification, validation, peer review, testing, quality metrics
Documentation           — Technical writing, knowledge publication, standards, user docs
Finance & Resources     — Budgets, cost optimisation, token accounting, compute allocation
Human Resources         — Agent lifecycle, competency management, performance, training
Enterprise Knowledge    — Corporate memory, knowledge governance, retrieval policies
Innovation Laboratory   — Research initiatives, experimental workflows, prototypes
```

Every capability SHALL have exactly one owning Department; multiple Departments MAY consume
a capability owned elsewhere (see §11 Capability Ownership).


# 29. Worked Department Examples (post-MVP illustration)

Adopted from RAS. These illustrate a more mature, multi-agent department structure — not
the MVP target. Each department here has 3-4 named specialist agent roles, versus the MVP's
one agent per department (FATS).

## Engineering Department

Capabilities: Software Development, Architecture, Testing, DevOps, Infrastructure.

Agents: Software Architect, Developer, Tester, DevOps Engineer.


## Legal & Compliance Department

Capabilities: Regulatory Analysis, Contract Review, Privacy Assessment, Risk Evaluation.

Agents: Legal Analyst, Compliance Officer, Privacy Specialist.


## Research Department

Capabilities: Information Discovery, Market Research, Scientific Analysis, Competitive Intelligence.

Agents: Research Analyst, Data Analyst, Strategist.


## Security Department

Capabilities: Threat Analysis, Security Architecture, Risk Assessment, Incident Analysis.

Agents: Security Analyst, Threat Specialist, Security Architect.


# 30. Design Philosophy

Departments are the organs of The Company.

Agents are the workers.

Capabilities are the expertise.

Workflows are the processes.

Policies are the controls.

Memory is the institutional knowledge.

A successful AI enterprise does not maximize the number of agents.

It creates the right organizational structure to apply intelligence where it creates the greatest value.

The Company is not a swarm.

It is an adaptive enterprise.
