# Stage: Generate Scenario
## Input: template_id, locale, seed
## Process: load template (validate), load locale, apply seeded random
  product choice, merge locale_rules into scenario payload.
## Output: full scenario JSON with locale-specific tax/freight/currency
## Completion: served at POST /scenarios/generate. Same seed = same output.
