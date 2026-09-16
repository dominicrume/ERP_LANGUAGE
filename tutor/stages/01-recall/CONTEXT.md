# Stage: Recall Learner
## Input: learner_id, template_id
## Process: query LearnerProgress — never merge across learners (Rule 5)
## Output: attempts, best_score, last_mistake, or "no attempts yet"
## Completion: served at GET /learners/{id}/progress/{template_id}.
  This is the "AI tutor remembers you across sessions" promise, delivered.
