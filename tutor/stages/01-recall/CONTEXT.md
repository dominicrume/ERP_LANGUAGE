# Stage: Recall Learner
## Input: learner_id, template_id, and optionally a locale
## Process: query LearnerProgress keyed learner x template x locale —
  never merge across learners (Rule 5), and never merge across locales:
  a score earned under UK rules says nothing about Nigeria rules.
## Output: with locale — attempts, best_score, last_mistake, or "no attempts
  yet". Without locale — the same learner's per-locale rows plus totals.
## Completion: served at GET /learners/{id}/progress/{template_id}[?locale=].
  This is the "AI tutor remembers you across sessions" promise, delivered.
