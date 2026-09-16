# Scaling Rules

1. SQLite for dev -> Postgres for real deployment. DSN swap only.
2. Template/locale files are the growth mechanism: N templates x M
   locales = N*M scenarios with zero new code. Instructor-authored
   templates (validated, see ENGINEERING.md #4) grow N without an engineer.
3. Frontend is a static single-file app calling a versioned API — it
   scales by CDN, not by server fleet. The API is the only stateful tier.
4. Multi-tenant (per-university) isolation is SEEDLING until a second
   paying institution is signed — see ROOTS-SCORE.md. Do not build
   speculative tenant infrastructure before the second buyer is real.
5. Cost discipline: scenario generation is deterministic and cheap (no
   LLM call). Any future AI-tutor conversational layer (BLUEPRINT-MAP.md)
   must be costed per learner-session before it ships, not after.
