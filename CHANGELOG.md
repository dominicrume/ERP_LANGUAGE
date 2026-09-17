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
- 2026-09-17 v0.4.0 — Instructor authoring surface (PRODUCT.md #5). The
  YAML textarea is replaced by a real builder: a shelf of published
  scenarios, a guided form (the situation / the decisions / what it
  measures), and a live preview that renders the draft in every country
  exactly as a learner will see it, with a strip that says plainly
  whether the scenario is genuinely localized or scores the same
  everywhere. Instructors write points and a reason in plain language
  with [country]-style tokens; they never see multiply_by, kpi_weights
  or a format spec. Publishing writes config/templates/{id}.yaml and
  archives any version it replaces, so adding an industry is still
  adding a config file (ENGINEERING.md #2) — just not by hand.
  New: src/erpsim/authoring.py, GET /instructor/templates, GET
  /instructor/drafts/{id}, POST /instructor/drafts/preview, POST
  /instructor/drafts/publish. generator.generate_from() previews an
  unsaved draft without touching config/. Scoring gained {delta} and
  {tax_percent} so authored reasons need no format specs.
  Tests 66 -> 110, including 5 Chromium tests that author, publish, play
  and re-edit a scenario through the UI alone (BREAK.md hat 2, answered).
  DEBT.md: instructor-authoring row repaid and removed; two new rows
  logged (unauthenticated publishing, no locale authoring surface).
- 2026-09-17 v0.4.1 - Frontend redesign and security fix, audited in a real
  browser before and after (taste-skill + ui-ux-pro-max). Security: authored
  decision labels and reasons were inserted into the learner view as raw
  HTML, and publishing is open, so any published scenario could run script
  in every learner's browser (proven: the probe executed twice). All
  authored text is now escaped and option ids travel in data attributes,
  never in inline handlers. Bugs: the flipped card clipped its reason on
  desktop and spilled over the next decision on mobile; keyboard focus
  stayed on the hidden front face, whose buttons could still be pressed to
  re-score; Publish stayed disabled after an error; a slow preview could
  overwrite a newer one; switching preview country re-fetched data the page
  already had. UI: design tokens with full dark mode, one accent, one gray
  family, one radius system; real labels on every control; header, main,
  nav landmarks and a skip link; visible focus rings; 44px targets on touch
  devices; skeleton loading, an empty state, and inline icons from
  Phosphor; zero em or en dashes in visible copy; the catalogue shown as
  "scenarios x countries = playable combinations". Honesty: the score bar
  no longer says "Running score" or "Attempts", because the API scores
  each decision on its own (CONTEXT.md gap A remains open until runs exist).
  Tests 110 -> 123. Measured: 0 contrast failures and 0 horizontal scroll
  in light and dark at 1280px and 375px. Pushed to
  github.com/dominicrume/ERP_LANGUAGE, merged with its starter commit, no
  force push.

