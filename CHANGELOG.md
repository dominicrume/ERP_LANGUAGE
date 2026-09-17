# Changelog
- 2026-09-16 v0.1.0 — runnable core: intake + WEEE-safe... (n/a, prior project)
- 2026-09-16 v0.2.0 — Frontend added: premium editorial UI (Newsreader +
  Instrument Sans), card-flip decision reveal, persistent-memory welcome
  strip, instructor catalog + template validator. Rules split into
  ENGINEERING/PRODUCT/SCALING; BREAK.md red-team protocol added.
  ROOTS re-scored: 9 rooted, 4 seedling (all HV, all dated + owned).
- 2026-09-17 v0.3.0 — Red-teamed against BREAK.md (PROMPT-01). Scoring
  rules moved from Python into template YAML; scoring.py is a generic
  interpreter (Rule 2 restored, heatwave_demand byte-identical by golden
  test). Fixes: (1) invalid choice 422s and never writes memory; (2)
  scoring as data, made_to_order now scores with reasons; (3) memory keyed
  learner x template x locale; (3b) scenario carries locale_id so non-UK
  scenarios can be scored back; (4) last_mistake persisted and shown on
  return; (5) a broken locale/template file 404s for itself only and is
  excluded from /catalog; (6) DSN from ERPSIM_DATABASE_URL; (7) in-product
  statement of what the learner's name is used for, collision logged in
  DEBT.md; (8) numeric assertion test per locale, four distinct outcomes
  proven; (9) frontend inline reconnecting state with one retry, running
  score from the API; (10) dead doc references fixed, DEBT.md created;
  (11) learner ids and config ids validated, no path joins from input.
  Tests 14 -> 65. `make check` = pytest + ROOTS gate. Git history begins
  at the v0.2.0 baseline.
