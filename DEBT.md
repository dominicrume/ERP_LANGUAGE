# DEBT.md — Known breaks we have chosen not to fix yet

Standing rule (BREAK.md): never ship an unlogged known break. Every row
has a repay trigger and an owner. Close a row by deleting it in the same
commit that repays it.

| Item | Found | Repay trigger | Owner |
|------|-------|---------------|-------|
| Learner identity is a bare name. Two people typing "frank" share one record, and anyone can read any learner's record by guessing their name. A run is protected (a named run refuses a different name) but the name itself is not proof of anything. PRODUCT.md #7 calls this a trust breach. Stated plainly in-product for now. | 2026-09-17, PROMPT-01 Fix 7 | Before first external pilot | Rume |
| Anyone who can reach the app can publish a scenario. The builder writes to config/templates/ with no instructor identity behind it. Fine for a local demo, not once it is hosted for a cohort. Same root cause as row 1. | 2026-09-17, builder release | Before the app is hosted anywhere a learner can reach it | Rume |
| Locales still have no authoring surface. Adding a country is a hand-written YAML file: fine for an engineer, impossible for a procurement officer who wants to see their own country in the demo. | 2026-09-17, builder release | When a prospect asks for a country we do not ship | Rume |
| The stateless POST /decisions/score still scores one decision on its own and writes the legacy attempts counter. Nothing in the product calls it any more; it is kept so anything built against v0.4 keeps working. | 2026-09-18, PROMPT-02 item 6 | Remove at the next breaking API version, once no client uses it | Rume |
| A learner can abandon a sitting and start another, and abandoned runs are never cleaned up. Harmless at demo scale, unbounded over a term. | 2026-09-18, PROMPT-02 item 1 | Before first external pilot, or when the runs table passes ~100k rows | Rume |
