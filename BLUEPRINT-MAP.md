# What runs now vs. what it graduates to

| Component              | Running now                          | Graduates to (funding/scale) |
|-------------------------|---------------------------------------|-------------------------------|
| Scenario templates      | YAML files, 2 industries              | Instructor UI authoring templates live |
| Locales                 | Brazil and the UK ship; Germany and Nigeria parked | Community-contributed locale packs |
| Learner memory           | SQLite, per learner x template        | Postgres, multi-tenant per university |
| Scoring engine           | Deterministic rules, per-decision     | Same rules + optional AI coaching commentary |
| AI tutor "conversation"  | Not built (Frank's gap, correctly)    | Chat layer ON TOP of this scoring engine — grounded, not freeform |
| Instructor authoring     | /instructor/templates/validate (schema check only) | Full web UI, versioning, publish workflow |

Frank's exact worry — "is this teaching, or just a dashboard?" — is
answered here: the AI tutor conversation is a thin layer that MUST sit on
top of this grounded scoring engine. Build the chat before this exists,
and you get Lovable's problem again: fluent, ungrounded, forgets in 3
months. Build it after, and every tutor response can cite the exact
locale rule and the learner's own history. That ordering is the product.
