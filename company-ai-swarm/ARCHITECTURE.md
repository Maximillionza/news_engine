# The Company — Architecture Pointer

This file is a pointer, not a duplicate. The authoritative architecture is defined in `Specifications/`.

## Reading order

1. `Specifications/1 - enterprise-architecture/Enterprise Architecture Framework (EAF).md` — master index, governance rules, dependency model.
2. `Specifications/1 - enterprise-architecture/` — what The Company is (AOSS, DOMS, EKGS, EWOS, EMAS, ESTAS, ECRIS, EOCCS, EESIS, EDIS).
3. `Specifications/2 - construction-framework/` — how it is built (TCAIS, EIB, TAS, ECAS, EIR, TCABS, CRBS, ADLS, ECLS).
4. `Specifications/3 - execution-framework/` — how construction is executed (ABMEP, RCS, DOR, MVS, CCBP).

## Governance rule

No document may contradict a document above it in the hierarchy (EAF §"Dependency Model"). This repository's folder structure follows `The Company Repository Blueprint Specification (CRBS)`.

## Status

This structure was scaffolded per CRBS. **All twelve phases (0-11) of `IMPLEMENTATION_PLAN.md` are implemented and tested** — see `CHANGELOG.md` for what each phase built, and `Documentation/operations/technology_decisions.md` for every dev/test-vs-production substitution and honesty note. The MVS-canonical MVP (Director + COO + Research/Engineering/Compliance/Operations departments + one agent each + full governance layer) was complete as of Phase 9 (MVP Version 1.0); Phase 10 (post-MVP Expansion Layer) added a real SDK (agent/capability/workflow builders), Plugin and Marketplace registries, and API Gateway endpoints wired to the COO; Phase 11 (post-MVP Intelligence Systems) added a Digital Twin state snapshot, a Workflow Simulation Engine, and the Evolution Engine improvement-proposal pipeline with human approval enforced as a hard gate. Several sub-components remain honest placeholders where a phase's own MVP scope didn't require them (e.g. the Scenario Generator and Behaviour/Resource Simulation Engines) — see each service's README for exactly what is and isn't built.
