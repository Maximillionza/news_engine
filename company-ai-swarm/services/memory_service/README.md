# Memory Service

Stores and retrieves governed organizational memory.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Memory Architecture Specification (EMAS).md

**Status:** `repository.py` (Phase 2): `write_memory`, `get_memory`, and `query_memory`
across all five canonical tiers (Working, Project, Department, Enterprise, Historical - EMAS
sec.5), with Project- and Department-tier isolation and every access routed through
security_service.authorize() (ESTAS sec.16). Phase 9 added `promotion.py`: memory promotion
between tiers (EMAS sec.15), specifically Project -> Historical, as the COOS sec.6 Learn
step's tiered mechanism (`orchestrator/controller.py._learn()`) - minor lessons go straight
to Historical, critical lessons (Phase 8 escalation policy) are held here as a
`LessonPromotion` pending human `approve_promotion()`/`reject_promotion()`. Approval always
writes a brand-new Historical-tier memory object rather than mutating the pending one in
place. Decay/expiration enforcement (EMAS sec.16) is still not implemented.

**Tests:** `Tests/integration/test_memory_substrate.py` (Phase 2),
`Tests/integration/test_lesson_promotion.py` (Phase 9).
