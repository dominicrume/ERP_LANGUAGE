# DEBT.md — Known breaks we have chosen not to fix yet

Standing rule (BREAK.md): never ship an unlogged known break. Every row
has a repay trigger and an owner. Close a row by deleting it in the same
commit that repays it.

| Item | Found | Repay trigger | Owner |
|------|-------|---------------|-------|
| Learner identity is a bare name. Two people typing "frank" share one record; anyone can GET any learner's progress by name. PRODUCT.md #7 calls this a trust breach. Mitigated for now by stating plainly in-product what the name is used for. Fix = per-institution learner accounts (not speculative auth — SCALING.md #4). | 2026-09-17, PROMPT-01 Fix 7 | Before first external pilot | Rume |
| Instructor authoring is a YAML validator, not an authoring surface. An instructor with no coding background cannot author a template through the UI alone today (PRODUCT.md #5, BREAK.md #2, ROOTS #4). The scoring block makes the YAML larger, not smaller. | 2026-09-17, PROMPT-01 hat 2 | v0.4 scenario-builder wizard, before first instructor onboarding | Rume |
| Hosted CI does not exist. The gate is `make check` run locally (scripts/check.sh); nothing enforces it on push because there is no remote yet. | 2026-09-17, PROMPT-01 release | Wire scripts/check.sh into hosted CI before first external pilot (ROOTS #12) | Rume |
