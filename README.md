# ERP Decision Lab — Localized Operational Decision-Support Training

The gap between high-level strategy simulations and daily ERP transaction
decisions — with real localization (tax, currency, freight, payment terms
per country), not just translated UI text.

## The thesis, provable in one command
    pytest tests/test_generator.py::test_localization_is_not_just_translation -v
Same template, two countries, genuinely different numeric rules. That test
passing is the whole pitch.

## Run it
    pip install -e .
    pytest                                    # 14 tests
    uvicorn erpsim.main:app --reload --app-dir src
    # open http://127.0.0.1:8000  <- the frontend, served automatically

## The experience (see rules/PRODUCT.md for the full standard)
A scenario reads like a short story. Each decision is a card — click an
option and it FLIPS to reveal the score and the plain-language reason,
citing the exact locale rule that produced it. Return with the same name
and template and the product greets you with your own history: attempts,
best score. Toggle to Instructor to see the template x locale catalog and
validate a new scenario before publishing it — no YAML tutorial required
to try, but it's still a YAML file underneath (ENGINEERING.md #2).

## Try it
    curl http://127.0.0.1:8000/catalog
    # -> 2 templates x 4 locales = 8 scenarios, zero extra code

    curl -X POST http://127.0.0.1:8000/scenarios/generate \
      -F template_id=heatwave_demand -F locale=nigeria -F seed=1

    curl -X POST http://127.0.0.1:8000/decisions/score \
      -F template_id=heatwave_demand -F locale=nigeria -F seed=1 \
      -F decision_id=freight_choice -F choice=expedite -F learner_id=frank

    curl http://127.0.0.1:8000/learners/frank/progress/heatwave_demand

## Adding a country or an industry
Add one YAML file. config/locales/ for a country, config/templates/ for an
industry. Zero code changes — see BLUEPRINT-MAP.md and rules/RULES.md Rule 2.

## What's deliberately NOT built yet
The AI tutor "conversation" layer (Frank's gap in his own Lovable MVP).
See BLUEPRINT-MAP.md — it must sit ON TOP of this grounded engine, never
replace it, or it inherits Lovable's exact failure: fluent but forgetful.
