# ROOTS-SCORE — ERP Decision Lab v0.4.0 · scored 2026-09-17 · owner: Rume
| # | Check | State | Pointer | Waiver |
|---|-------|-------|---------|--------|
| 1 | Written rules | ROOTED | rules/ENGINEERING.md, PRODUCT.md, SCALING.md, BREAK.md, DEBT.md + root CLAUDE.md | |
| 2 | Spec-first | ROOTED | stage CONTEXT.md files predate code and were updated with Fixes 3/3b; PRODUCT.md UX spec predates frontend | |
| 3 | Decomposition | ROOTED | 3 backend workspaces + static/ frontend, module-per-concern; scoring is an interpreter over template data | |
| 4 | Planning [HV] | ROOTED | instructor builder ships: shelf + guided authoring + cross-locale preview + publish (static/index.html, src/erpsim/authoring.py), proven in Chromium by tests/test_builder_browser.py | |
| 5 | Exit criteria | ROOTED | Completion clause in every CONTEXT.md; PROMPT-01 §5 exit criteria all met by tests | |
| 6 | Context discipline | ROOTED | L1 tables x4; frontend calls API only — tests/test_frontend_contract.py greps for zero scoring/locale arithmetic in JS | |
| 7 | Sandboxing [HV] | SEEDLING | | Rume 2026-09-16: single-process v0.1; per-tenant isolation at 2nd paying institution (SCALING.md #4) |
| 8 | Trajectory [HV] | ROOTED | last_mistake now actually written (tests/test_api.py::test_negative_decision_records_last_mistake) and shown in the welcome strip | |
| 9 | Guardrails | ROOTED | choice/decision/id validation 422/404; broken config file isolated (tests/test_broken_config.py); template scoring validated at authoring time | |
| 10 | Verification | ROOTED | tests/ 110 tests incl. golden scoring regression, zero-code growth proof and 5 real-browser authoring tests; scripts/check.sh gate | |
| 11 | Grounding [HV] | ROOTED | every option's reason template cites locale fields (tests/test_scoring.py::test_every_option_of_every_template_scores_with_a_reason); shown verbatim in UI | |
| 12 | CI/CD [HV] | SEEDLING | scripts/check.sh + `make check` (pytest then check_roots.py, non-zero on failure) | Rume 2026-09-17: no hosted CI/remote yet — DEBT.md row 2; wire before first external pilot |
| 13 | Feedback [HV] | ROOTED | attempts, best score and last mistake recorded per learner x template x locale -> visible memory strip on return | |
