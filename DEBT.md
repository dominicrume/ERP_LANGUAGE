# DEBT.md — Known breaks we have chosen not to fix yet

Standing rule (BREAK.md): never ship an unlogged known break. Every row
has a repay trigger and an owner. Close a row by deleting it in the same
commit that repays it.

| Item | Found | Repay trigger | Owner |
|------|-------|---------------|-------|
| Learner identity is a bare name. Two people typing "frank" share one record; anyone can GET any learner's progress by name. PRODUCT.md #7 calls this a trust breach. Mitigated for now by stating plainly in-product what the name is used for. Fix = per-institution learner accounts (not speculative auth — SCALING.md #4). | 2026-09-17, PROMPT-01 Fix 7 | Before first external pilot | Rume |
