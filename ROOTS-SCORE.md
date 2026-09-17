# ROOTS-SCORE — ERP Decision Lab v1.0.0 · scored 2026-09-18 · owner: Rume
| # | Check | State | Pointer | Waiver |
|---|-------|-------|---------|--------|
| 1 | Written rules | ROOTED | rules/ENGINEERING.md, PRODUCT.md, SCALING.md, BREAK.md, DEBT.md + root CLAUDE.md | |
| 2 | Spec-first | ROOTED | stage CONTEXT.md files predate code and were updated with Fixes 3/3b; PRODUCT.md UX spec predates frontend | |
| 3 | Decomposition | ROOTED | 3 backend workspaces + static/ frontend, module-per-concern; scoring is an interpreter over template data | |
| 4 | Planning [HV] | ROOTED | instructor builder ships: shelf + guided authoring + cross-locale preview + publish (static/index.html, src/erpsim/authoring.py), proven in Chromium by tests/test_builder_browser.py | |
| 5 | Exit criteria | ROOTED | Completion clause in every CONTEXT.md; PROMPT-01 §5 exit criteria all met by tests | |
| 6 | Context discipline | ROOTED | L1 tables x4; frontend calls API only — tests/test_frontend_contract.py greps for zero scoring/locale arithmetic in JS | |
| 7 | Sandboxing [HV] | SEEDLING | | Rume 2026-09-18: single-process v1.0; per-tenant isolation at 2nd paying institution (SCALING.md #4) |
| 8 | Trajectory [HV] | ROOTED | a run records every decision with its reason, completes with a final score, and feeds runs_completed, best_run_score and a streak (tests/test_runs.py, tests/test_learner_run_browser.py) | |
| 9 | Guardrails | ROOTED | choice/decision/id validation 422/404; broken config file isolated (tests/test_broken_config.py); template scoring validated at authoring time | |
| 10 | Verification | ROOTED | tests/ 202 tests: two scoring goldens (legacy + weighted), zero-code growth, migration upgrade of a seeded v0.4 database, 18 real-browser tests across learner sittings, authoring, stored-XSS and UI quality in light and dark; scripts/check.sh gate proves migrations too | |
| 11 | Grounding [HV] | ROOTED | every score carries its reason and now its per-KPI arithmetic, whose rows add up to the delta (tests/test_kpi_weighting.py); shown verbatim in the card and the completion summary | |
| 12 | CI/CD [HV] | ROOTED | .github/workflows/check.yml runs scripts/check.sh (migrations, 202 tests incl. Chromium, ROOTS) on every push and pull request to github.com/dominicrume/ERP_LANGUAGE | |
| 13 | Feedback [HV] | ROOTED | finished sittings, best run, streak and last mistake per learner x template x locale -> completion card at the end and welcome strip on return | |
