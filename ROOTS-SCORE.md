# ROOTS-SCORE — ERP Decision Lab (with frontend) · scored 2026-09-16 · owner: Rume
| # | Check | State | Pointer | Waiver |
|---|-------|-------|---------|--------|
| 1 | Written rules | ROOTED | rules/ENGINEERING.md, PRODUCT.md, SCALING.md + root CLAUDE.md | |
| 2 | Spec-first | ROOTED | stage CONTEXT.md files predate code; PRODUCT.md UX spec predates frontend | |
| 3 | Decomposition | ROOTED | 3 backend workspaces + static/ frontend, module-per-concern | |
| 4 | Planning [HV] | SEEDLING | | Rume 2026-09-16: fixed flow for v0.1; instructor scenario-builder wizard in v0.2 |
| 5 | Exit criteria | ROOTED | Completion clause in every CONTEXT.md | |
| 6 | Context discipline | ROOTED | L1 tables x4; frontend calls API only, no logic duplication (ENGINEERING.md #6) | |
| 7 | Sandboxing [HV] | SEEDLING | | Rume 2026-09-16: single-process v0.1; per-tenant isolation at 2nd paying institution (SCALING.md #4) |
| 8 | Trajectory [HV] | ROOTED | scoring.justification + memory.last_mistake; frontend reveals both to the learner | |
| 9 | Guardrails | ROOTED | template validation fails loud; unknown locale/template -> 404; BREAK.md red-team log | |
| 10 | Verification | ROOTED | tests/ 14 tests + live E2E smoke test (frontend->API->DB round trip confirmed) | |
| 11 | Grounding [HV] | ROOTED | every score's justification cites the specific locale rule, shown verbatim in the UI | |
| 12 | CI/CD [HV] | SEEDLING | check_roots.py exists | Rume 2026-09-16: wire into pipeline before first external pilot |
| 13 | Feedback [HV] | ROOTED | operator/learner attempts recorded -> visible memory strip on return visit | |
