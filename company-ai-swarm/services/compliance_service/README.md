# Compliance Service

Evaluates regulatory applicability and risk.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Compliance and Regulatory Intelligence Specification (ECRIS).md

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 8, MVP Build Order Version 0.4).

- `applicability.py` - `assess_applicability()` (ECRIS sec.8): Business Activity + Location +
  Data Type + Industry + Entity Type + Risk Profile -> Regulatory Applicability, via a small,
  explicit rule registry (ECRIS sec.9's Compliance Knowledge Model). One seeded rule (POPIA,
  taken directly from ECRIS sec.8's own worked example) - populating a real regulatory rule
  set is content curation, out of scope here. An unrecognized regulation returns
  `applicable=None` (UNKNOWN), never a silent `False` - see module docstring.
- `policy_impact.py` - `analyze_policy_impact()` (MVS sec.12, Test Category 008): Policy
  Added -> Impact Analysis -> Workflow Review -> Control Recommendation. Impact Analysis
  reuses `orchestrator/classification.py`'s keyword-overlap mechanism (originally
  `orchestrator/planner.py`'s) against department capabilities, not a second matcher;
  Control Recommendation is a templated string, not AI-generated (no real model is wired
  anywhere in this corpus).

**Tests:** `Tests/integration/test_compliance_intelligence.py`
