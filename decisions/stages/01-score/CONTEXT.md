# Stage: Score Decision
## Input: scenario + decision_id + learner's choice
## Process: apply locale-aware scoring rules; same choice scores
  differently under different locale_rules (proven by test).
## Output: score_delta, running_score, justification[] (provenance)
## Completion: if learner_id given, record_attempt() persists to memory.
