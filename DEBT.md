# DEBT.md — Known breaks we have chosen not to fix yet

Standing rule (BREAK.md): never ship an unlogged known break. Every row
has a repay trigger and an owner. Close a row by deleting it in the same
commit that repays it.

| Item | Found | Repay trigger | Owner |
|------|-------|---------------|-------|
| Learner identity is a bare name. Two people typing "frank" share one record; anyone can GET any learner's progress by name. PRODUCT.md #7 calls this a trust breach. Mitigated for now by stating plainly in-product what the name is used for. Fix = per-institution learner accounts (not speculative auth — SCALING.md #4). | 2026-09-17, PROMPT-01 Fix 7 | Before first external pilot | Rume |
| Hosted CI does not exist. The gate is `make check` run locally (scripts/check.sh); nothing enforces it on push because there is no remote yet. | 2026-09-17, PROMPT-01 release | Wire scripts/check.sh into hosted CI before first external pilot (ROOTS #12) | Rume |
| Anyone who can reach the API can publish a scenario. The builder writes to config/templates/ with no instructor identity behind it. Acceptable while the only deployment is a local demo; not acceptable the moment it is hosted for a cohort. Same root cause as row 1. | 2026-09-17, builder release | Before the app is hosted anywhere a learner can reach it | Rume |
| Locales still have no authoring surface. Adding a country is a hand-written YAML file — fine for an engineer, impossible for a procurement officer who wants to see their own country in the demo. | 2026-09-17, builder release | When a prospect asks for a country we do not ship | Rume |
