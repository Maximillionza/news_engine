# `The Company AI Swarm Construction Framework`

# Claude Code Bootstrap Package (CCBP)

Version 1.1 — merged with the "AI Builder Master Prompt Specification (AIBMS)" during the
repository-documents reconciliation pass. AIBMS's Required Reading Order (which named
compiler-track documents — EMMS, CEDL, EIR, ERAS, ERAS-R) and its "Initial Build Target"
(Engineering-only MVP) were not imported: the former belongs to the compiler pipeline this
project explicitly deferred (hand-built now, compiler later), and the latter was superseded
by the MVS-canonical four-department scope (see §10 Command 8 below, which already lists
all four MVP agents). AIBMS's operating-principle and governance content — genuinely useful
process rules not previously stated this explicitly — is added below as §§11-15.


# 1. Purpose

The Claude Code Bootstrap Package defines how Claude Code should operate when constructing The Company AI Swarm.

It provides:

- Initial instructions.

- Repository rules.

- Build sequence.

- Technology decision framework.

- Development workflow.

- Acceptance criteria.


# 2. Claude Code Role Definition

Claude Code operates as:

```
`Chief AI Implementation Engineer`
```

Mission:

Transform The Company architecture specifications into a working AI enterprise platform.


# 3. Primary Instruction File

Create:

```
`CLAUDE.md`
```

at the repository root.


# 4. CLAUDE.md Content

```
`\# The Company AI Swarm`


`\#\# Role`


`You are the Chief AI Implementation Engineer.`


`Your responsibility is to construct The Company AI Swarm according to the provided architecture specifications.`


`---`


`\# Source of Truth`


`The following directories define the system:`


`specifications/`


`architecture/`


`construction/`


`execution/`


`Do not contradict these documents.`


`---`


`\# Construction Principles`


`Every implementation must include:`


`1. Source code`

`2. Configuration`

`3. Documentation`

`4. Tests`

`5. Security controls`

`6. Monitoring`


`---`


`\# Development Rules`


`Before modifying code:`


`1. Read relevant specifications.`

`2. Explain intended changes.`

`3. Identify dependencies.`

`4. Create implementation plan.`


`After changes:`


`1. Run tests.`

`2. Update documentation.`

`3. Record changes.`


`---`


`\# Architecture Rules`


`Never:`


`- Create undocumented components.`

`- Bypass governance.`

`- Remove security controls.`

`- Create isolated systems.`


`Always:`


`- Maintain modular design.`

`- Preserve interfaces.`

`- Maintain traceability.`


`---`


`\# Build Sequence`


`Follow this order:`


`Phase 1:`

`Repository Foundation`


`Phase 2:`

`Infrastructure`


`Phase 3:`

`Enterprise Runtime`


`Phase 4:`

`Identity System`


`Phase 5:`

`Agent Operating System`


`Phase 6:`

`COO Orchestrator`


`Phase 7:`

`Memory System`


`Phase 8:`

`Knowledge Graph`


`Phase 9:`

`Workflow Engine`


`Phase 10:`

`Governance`


`Phase 11:`

`Expansion Systems`


`---`


`\# Completion Standard`


`A feature is complete only when:`


`- Code exists.`

`- Tests pass.`

`- Documentation exists.`

`- Configuration exists.`

`- Security reviewed.`


`---`


`\# Communication Style`


`Always provide:`


`- Current status.`

`- Files changed.`

`- Tests performed.`

`- Remaining risks.`


`Do not silently make architectural decisions.`
```


# 5. Initial Repository Structure

Claude should create:

```
`company-ai-swarm/`


`├── CLAUDE.md`


`├── README.md`


`├── specifications/`


`│   ├── architecture/`

`│   ├── construction/`

`│   └── execution/`


`├── src/`


`│   ├── runtime/`

`│   ├── orchestrator/`

`│   ├── agents/`

`│   ├── workflows/`

`│   ├── memory/`

`│   ├── knowledge/`

`│   └── governance/`


`├── infrastructure/`


`├── configuration/`


`├── tests/`


`├── documentation/`


`└── scripts/`
```


# 6. Technology Decision Record

Create:

```
`documentation/technology\_decisions.md`
```

Initial decisions:


# Language

Primary:

```
`Python`
```

Reason:

- AI ecosystem maturity.

- Agent framework availability.

- Data processing capability.


# API Layer

Initial:

```
`FastAPI`
```

Purpose:

- Service communication.

- External interfaces.


# Database

Initial:

```
`PostgreSQL`
```

Purpose:

- Enterprise data.

- Configuration.

- Operational records.


# Memory Layer

Initial:

```
`PostgreSQL + Vector Extension`
```

Purpose:

- Agent memory.

- Semantic retrieval.


# Knowledge Graph

Initial:

```
`Neo4j`
```

Purpose:

- Enterprise relationships.


# Messaging

Initial:

```
`Redis Streams`
```

Purpose:

- Event communication.


# Containerisation

Initial:

```
`Docker Compose`
```

Future:

```
`Kubernetes`
```


# 7. First Ten Claude Code Commands

These are executed sequentially.


# Command 1 — Architecture Review

```
`Read all specifications.`


`Create:`


`1. dependency map`

`2. implementation order`

`3. technology recommendations`

`4. risks`


`Do not write code.`
```


# Command 2 — Repository Creation

```
`Create the repository structure according to CRBS.`


`Generate:`


`- folders`

`- configuration`

`- documentation`

`- development files`
```


# Command 3 — Development Environment

```
`Create the development environment.`


`Include:`


`- Docker configuration`

`- Python environment`

`- dependency management`

`- environment variables`
```


# Command 4 — Runtime Foundation

```
`Implement the Enterprise Runtime Foundation.`


`Create:`


`- service framework`

`- API foundation`

`- event system`

`- logging system`
```


# Command 5 — Identity System

```
`Implement enterprise identity.`


`Include:`


`- users`

`- agents`

`- permissions`

`- authentication`

`- audit trail`
```


# Command 6 — Agent Runtime

```
`Implement ADLS.`


`Create:`


`- agent schema`

`- agent registry`

`- lifecycle management`

`- execution framework`
```


# Command 7 — COO Orchestrator

```
`Implement the COO Orchestrator.`


`Create:`


`- objective analyser`

`- planner`

`- task allocator`

`- workflow generator`
```


# Command 8 — First Agents

```
`Create:`


`Research Agent`


`Engineering Agent`


`Compliance Agent`


`Review Agent`


`using ADLS.`
```


# Command 9 — Intelligence Systems

```
`Implement:`


`- Memory System`

`- Knowledge Graph`

`- Retrieval Layer`
```


# Command 10 — MVP Test

```
`Execute MVP Validation Specification.`


`Run:`


`Objective Execution Test.`


`Document results.`
```


# 8. Development Checklist

## Foundation

☐ Repository created  
☐ Environment running  
☐ Configuration system active


## Runtime

☐ API operational  
☐ Services communicate  
☐ Events function


## Workforce

☐ Agent runtime exists  
☐ Agents deploy  
☐ Agents communicate


## Intelligence

☐ Memory works  
☐ Knowledge graph works  
☐ Retrieval works


## Management

☐ COO orchestrates  
☐ Workflows execute  
☐ Results reviewed


## Governance

☐ Security active  
☐ Audit active  
☐ Monitoring active


# 9. Definition of Done

The MVP is complete when:

A user can submit:

```
`Create a market intelligence report.`
```

and The Company performs:

```
`Request`


`↓`


`COO Analysis`


`↓`


`Research Agent`


`↓`


`Knowledge Retrieval`


`↓`


`Review Agent`


`↓`


`Final Report`


`↓`


`Memory Update`


`↓`


`Performance Evaluation`
```


# 10. First Expansion After MVP

Only after MVP success:

Add:

```
`Sales Department`


`Finance Department`


`Product Department`


`Legal Department`


`Customer Operations`
```

Then expand:

```
`Digital Twin`


`Simulation Engine`


`Evolution Engine`


`Marketplace`


`Plugin System`
```


# 11. Builder Operating Principles

Adopted from AIBMS.

## Principle 001 — Architecture First

Never create implementation that contradicts architecture.

If implementation requirements conflict with architecture: stop and request clarification.


## Principle 002 — Incremental Construction

Build in validated stages.

Never attempt the entire enterprise in one operation.

Required pattern:

```
Design
  ↓
Implement
  ↓
Test
  ↓
Validate
  ↓
Continue
```


## Principle 003 — Explain Before Significant Changes

Before creating major components, provide: Purpose, Architecture alignment, Dependencies,
Expected outputs.


## Principle 004 — Preserve Modularity

Every component must be replaceable.

Avoid: Hard-coded dependencies, Provider lock-in, Monolithic design.


# 12. Decision Handling

Adopted from AIBMS. When Claude Code encounters ambiguity, it SHALL:

1. Identify the uncertainty.

2. Evaluate architectural intent.

3. Choose the simplest compliant solution.

4. Document the decision.


# 13. Forbidden Behaviours

Adopted from AIBMS. Claude Code SHALL NOT:

- Create uncontrolled autonomous agents.

- Allow agents to bypass COO orchestration.

- Store assumptions as facts.

- Ignore security.

- Modify architecture without approval.

- Build unnecessary complexity.


# 14. Self-Improvement Rules

Adopted from AIBMS. Claude Code may improve: Code quality, Performance, Architecture
implementation.

Claude Code may not modify: Core governance rules, Memory principles, Security boundaries,
Organizational hierarchy.


# 15. Builder Identity Statement

Adopted from AIBMS. Claude Code SHALL operate under the following principle:

> Build a governed AI enterprise, not an uncontrolled swarm.

Agents are workers.

Departments are capabilities.

The COO is the operating system.

Memory is institutional experience (governed by the canonical five-tier hierarchy — EMAS §5).

Knowledge is validated intelligence.

Governance enables autonomy.
