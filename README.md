# ERP Decision Lab — Localized Operational Decision-Support Training

The gap between high-level strategy simulations and daily ERP transaction
decisions — with real localization (tax, currency, freight, payment terms
per country), not just translated UI text.

## The thesis, provable in one command
    pytest tests/test_generator.py::test_localization_is_not_just_translation -v
Same template, two countries, genuinely different numeric rules. That test
passing is the whole pitch. Its stronger sibling:
    pytest tests/test_zero_code_growth.py -v
A fifth country and a third industry, as two YAML files in a temp dir,
generate and score through the API with src/ untouched.

## Run it
    python3 -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]" httpx
    make check                                # 123 tests, then the ROOTS gate
    uvicorn erpsim.main:app --reload --app-dir src
    # open http://127.0.0.1:8000  <- the frontend, served automatically

Database: SQLite at ./erpsim.db by default. Set ERPSIM_DATABASE_URL to
any SQLAlchemy DSN (e.g. postgresql+psycopg2://user:pw@host/erpsim) to
swap it — no code change (SCALING.md #1).

## The experience (see rules/PRODUCT.md for the full standard)
A scenario reads like a short story. Each decision is a card — click an
option and it FLIPS to reveal the score and the plain-language reason,
citing the exact locale rule that produced it. Return with the same name,
template and country and the product greets you with your own history:
attempts, best score, and what tripped you up last time. If the API
drops mid-scenario you see an honest "retrying" strip, not a broken card,
and your scenario stays on screen.

## Instructors author scenarios, they don't edit config
Toggle to Instructor. You get a shelf of what's published and a builder
that asks for the situation, the decisions, and what the scenario
measures — in those words. You write what each choice costs and why, and
say whether the local market changes it; you never meet a format spec, a
weight that must sum to 1.0, or the word `multiply_by`.

The panel beside the form renders your draft in every country as the
learner will see it, and tells you plainly whether it is genuinely
localized or scores the same everywhere. Publishing is one button and
writes `config/templates/{id}.yaml` — adding an industry is still adding
a config file (ENGINEERING.md #2), just not by hand. Replacing a
scenario keeps the version you replaced.

Prove it without reading the code:

    pip install -e ".[ui]" && playwright install chromium
    pytest tests/test_builder_browser.py -v

Five Chromium tests author a scenario through the UI alone, publish it,
play it as a learner in Brazil, and reopen it for editing. They skip
loudly if Playwright is missing — a skip means unverified, not passed.

## Try it
    curl http://127.0.0.1:8000/catalog
    # -> 2 templates x 4 locales = 8 scenarios, zero extra code

    curl -X POST http://127.0.0.1:8000/scenarios/generate \
      -F template_id=heatwave_demand -F locale=nigeria -F seed=1
    # -> the scenario carries locale_id=nigeria; post that back when scoring

    curl -X POST http://127.0.0.1:8000/decisions/score \
      -F template_id=heatwave_demand -F locale=nigeria -F seed=1 \
      -F decision_id=freight_choice -F choice=expedite -F learner_id=frank
    # -> -42.0 pts, because Nigeria's expedite multiplier is 2.1x (UK: -32.0)

    curl "http://127.0.0.1:8000/learners/frank/progress/heatwave_demand?locale=nigeria"
    # -> attempts, best_score, last_mistake for frank x heatwave_demand x nigeria

    curl http://127.0.0.1:8000/learners/frank/progress/heatwave_demand
    # -> the same learner's per-locale rows plus totals; never another learner's

    curl -X POST http://127.0.0.1:8000/decisions/score \
      -F template_id=heatwave_demand -F locale=nigeria -F seed=1 \
      -F decision_id=freight_choice -F choice=teleport
    # -> 422: choice 'teleport' is not an option. Nothing is recorded.

## Adding a country or an industry
Add one YAML file. config/locales/ for a country, config/templates/ for an
industry. Zero code changes — see BLUEPRINT-MAP.md and rules/ENGINEERING.md Rule 2.

You can also write the file by hand. A template carries its own scoring:
every option declares `points`, a
`reason` template (may reference locale, currency, choice, points and any
locale_rules field), and optionally `multiply_by` one locale_rules field
so the same choice scores differently per country. Validation fails loud
on any option without a rule. See config/templates/heatwave_demand.yaml.

A locale file needs code, currency, tax {type, standard_rate, notes},
freight_expedite_multiplier and payment_terms_days. A file that does not
parse or misses a key is skipped from the catalog and logged by name —
the rest of the API keeps working.

Every shipped locale has a numeric assertion test (tests/test_locales.py);
one without is not a supported locale (scenarios/stages/02-localize).

## Known debt
DEBT.md. Every row has a repay trigger and an owner. BREAK.md is the
red-team protocol that produced it.

## What's deliberately NOT built yet
The AI tutor "conversation" layer (Frank's gap in his own Lovable MVP).
See BLUEPRINT-MAP.md — it must sit ON TOP of this grounded engine, never
replace it, or it inherits Lovable's exact failure: fluent but forgetful.
