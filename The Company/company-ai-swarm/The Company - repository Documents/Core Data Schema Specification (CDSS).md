# The Company AI Swarm Construction Framework

# Core Data Schema Specification (CDSS)

Version 1.0


# 1. Purpose

The Core Data Schema Specification defines the foundational data structures required to implement The Company AI Enterprise Operating System.

These schemas provide the common language between:

- Director.

- COO.

- Departments.

- Agents.

- Workflows.

- Memory systems.

- Knowledge systems.

- Model routing.

All components SHALL use these schemas.


# 2. Schema Design Principles

## Principle 001 — Universal Identity

Every enterprise object must have:

- Unique identifier.

- Name.

- Type.

- Status.

- Creation information.


## Principle 002 — Traceability

Every decision and action must be traceable.

Objects must support:

- Source.

- Owner.

- Timestamp.

- History.


## Principle 003 — Extensibility

Schemas must allow future capabilities without redesign.


# 3. Enterprise Object Model

The Company consists of:

```
`Enterprise`


`├── Departments`


`│       └── Agents`


`│`

`├── Workflows`


`│`

`├── Tasks`


`│`

`├── Knowledge`


`│`

`├── Memory`


`│`

`└── Models`
```


# 4. Enterprise Schema

Represents The Company itself.

```
`enterprise:`


`  id:`


`  name:`


`  version:`


`  mission:`


`  objectives:`


`  departments:`


`  governance\_rules:`


`  capabilities:`


`  status:`


`  created\_at:`


`  updated\_at:`
```


# 5. Department Schema

Defines organizational units.

```
`department:`


`  id:`


`  name:`


`  mission:`


`  purpose:`


`  capabilities:`


`  responsibilities:`


`  roles:`


`  agents:`


`  workflows:`


`  knowledge\_scope:`


`  permissions:`


`  metrics:`


`  status:`
```


# 6. Role Schema

Defines employee-type responsibilities.

```
`role:`


`  id:`


`  title:`


`  department:`


`  responsibilities:`


`  required\_capabilities:`


`  permissions:`


`  evaluation\_metrics:`
```


# 7. Agent Schema

Defines AI workers.

```
`agent:`


`  id:`


`  name:`


`  department:`


`  role:`


`  purpose:`


`  capabilities:`


`  tools:`


`  permissions:`


`  model\_requirements:`


`  memory\_scope:`


`  knowledge\_access:`


`  operating\_rules:`


`  evaluation:`


`  status:`
```


# 8. Agent Capability Schema

Defines what an agent can do.

```
`capability:`


`  id:`


`  name:`


`  description:`


`  complexity\_level:`


`  required\_tools:`


`  required\_models:`


`  limitations:`


`  validation\_method:`
```


# 9. Task Schema

Defines units of work.

```
`task:`


`  id:`


`  objective:`


`  description:`


`  requester:`


`  priority:`


`  complexity:`


`  risk:`


`  required\_capabilities:`


`  assigned\_department:`


`  assigned\_agent:`


`  workflow:`


`  inputs:`


`  outputs:`


`  status:`


`  created\_at:`


`  completed\_at:`
```


# 10. Task Complexity Schema

Used by COO model routing.

```
`complexity:`


`  reasoning\_required:`


`  technical\_depth:`


`  uncertainty:`


`  impact:`


`  time\_requirement:`


`  score:`
```

Example:

```
`Low:`


`Simple formatting.`


`Medium:`


`Research and analysis.`


`High:`


`Architecture or strategic reasoning.`
```


# 11. Workflow Schema

Defines processes.

```
`workflow:`


`  id:`


`  name:`


`  purpose:`


`  trigger:`


`  steps:`


`  dependencies:`


`  agents:`


`  approval\_points:`


`  failure\_handling:`


`  outputs:`


`  status:`
```


# 12. Workflow Step Schema

Defines individual execution steps.

```
`workflow\_step:`


`  id:`


`  order:`


`  action:`


`  assigned\_agent:`


`  required\_capabilities:`


`  inputs:`


`  outputs:`


`  validation:`
```


# 13. Memory Schema

Defines institutional memory.

All memory must identify its category.


## Working Memory

Temporary execution context.

```
`working\_memory:`


`  task\_id:`


`  context:`


`  current\_state:`


`  temporary\_information:`


`  expiry:`
```


## Episodic Memory

Past experiences.

```
`episodic\_memory:`


`  project:`


`  event:`


`  outcome:`


`  lessons:`


`  context:`


`  confidence:`


`  relevance:`
```


## Semantic Memory

Validated knowledge.

```
`semantic\_memory:`


`  fact:`


`  source:`


`  validation:`


`  confidence:`


`  relationships:`
```


## Procedural Memory

Methods and processes.

```
`procedural\_memory:`


`  procedure:`


`  purpose:`


`  steps:`


`  success\_conditions:`


`  limitations:`
```


# 14. Memory Governance Rules

Memory records SHALL include:

```
`memory\_metadata:`


`  source:`


`  timestamp:`


`  confidence:`


`  applicability:`


`  scope:`


`  validation\_status:`
```


Memory SHALL NOT automatically become policy.


# 15. Knowledge Schema

Defines enterprise knowledge.

```
`knowledge:`


`  id:`


`  entity:`


`  type:`


`  description:`


`  relationships:`


`  source:`


`  confidence:`


`  validation:`


`  owner:`


`  created\_at:`
```


# 16. Knowledge Relationship Schema

Defines connections.

```
`relationship:`


`  source\_entity:`


`  relationship\_type:`


`  target\_entity:`


`  confidence:`


`  evidence:`
```


# 17. Model Schema

Defines AI models available.

```
`model:`


`  id:`


`  provider:`


`  capability:`


`  reasoning\_level:`


`  cost:`


`  speed:`


`  limitations:`


`  availability:`
```


# 18. Model Routing Record

Records COO decisions.

```
`model\_selection:`


`  task:`


`  complexity:`


`  selected\_model:`


`  reason:`


`  alternatives:`


`  timestamp:`
```


# 19. Decision Record Schema

Every major decision must be stored.

```
`decision:`


`  id:`


`  decision\_type:`


`  decision:`


`  reasoning:`


`  inputs:`


`  responsible\_agent:`


`  confidence:`


`  timestamp:`
```


# 20. Audit Record Schema

Defines accountability.

```
`audit:`


`  event:`


`  actor:`


`  action:`


`  timestamp:`


`  result:`


`  related\_task:`
```


# 21. Initial Database Mapping

Recommended storage:

| **Schema** | **Storage** |
| :-: | :-: |
| Enterprise | PostgreSQL |
| Department | PostgreSQL |
| Agent | PostgreSQL |
| Tasks | PostgreSQL |
| Workflows | PostgreSQL |
| Memory | Vector Database + PostgreSQL |
| Knowledge | Graph Database |
| Documents | Object Storage |
| Logs | Observability Platform |


# 22. Schema Validation Rules

Before an object becomes active:

Validate:

```
`Identity exists`


`↓`


`Required fields exist`


`↓`


`Permissions defined`


`↓`


`Relationships valid`


`↓`


`Tests pass`


`↓`


`Activate`
```


# 23. Minimum Required Objects for MVP

The first deployment requires:

```
`1 Enterprise`


`1 Director`


`1 COO`


`1 Department`


`3 Agents`


`5 Capabilities`


`Task Schema`


`Workflow Schema`


`Memory Schema`


`Knowledge Schema`
```


# 24. Completion Criteria

The schema layer is complete when:

✓ Agents can be defined  
✓ Departments can be defined  
✓ Tasks can be created  
✓ Workflows can execute  
✓ Memory can persist  
✓ Knowledge can be represented  
✓ Decisions can be audited  
✓ Models can be selected
