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

This structure was scaffolded per CRBS. No functional code has been implemented — every file under `apps/`, `services/`, `agents/`, `sdk/`, `plugins/`, `marketplace/`, `simulation/`, `digital_twin/` is a placeholder or configuration template, not a working implementation.
