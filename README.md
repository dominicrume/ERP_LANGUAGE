# ERP Decision Lab — Localized Operational Decision-Support Training

The gap between high-level strategy simulations and daily ERP transaction
decisions — with real localization (tax, currency, freight, payment terms
per country), not just translated UI text.

## What a learner does
Pick a scenario and a country, read a short story, and turn over one card
per decision. Each card shows what the choice cost, the local rule behind
it, and the running total for the sitting. At the end you get a score out
of 100, every decision with its reason, the one that cost the most, and
your streak. Play the same story in another country and the numbers change.

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
    make check                                # migrations, 203 tests, then the ROOTS gate
    uvicorn erpsim.main:app --reload --app-dir src
    # open http://127.0.0.1:8000  <- the frontend, served automatically

Database: SQLite at ./erpsim.db by default. Set ERPSIM_DATABASE_URL to
any SQLAlchemy DSN (e.g. postgresql+psycopg2://user:pw@host/erpsim) to
swap it, with no code change (SCALING.md #1). The schema is versioned:
startup applies pending migrations, and `make migrate` applies them by hand.

## The experience (see rules/PRODUCT.md for the full standard)
A scenario reads like a short story. Each decision is a card — click an
option and it FLIPS to reveal the score and the plain-language reason,
citing the exact locale rule that produced it, and the running total for
the sitting. Finish every card and you get the scenario's own score out of
100. Return with the same name, template and country and the product greets
you with your own history: sittings finished, best score, day streak, and
what tripped you up last time. If the connection drops mid-scenario you see
an honest "retrying" strip, and the sitting itself lives on the server, so
reloading picks up where you left off.

## Instructors author scenarios, they don't edit config
Toggle to Instructor. You get a shelf of what's published and a builder
that asks for the situation, the decisions, and what the scenario
measures, in those words. For each choice you say which measures it moves,
by how much, and whether the local market changes it. You never meet a
format spec, a weight that must sum to 1.0, or the words `impact`,
`scales_with` or `kpi_weights`.

The panel beside the form renders your draft in every country as the
learner will see it, tells you plainly whether it is genuinely localized or
scores the same everywhere, and shows the best and worst score a learner
could finish on. Publishing is one button and
writes `config/templates/{id}.yaml` — adding an industry is still adding
a config file (ENGINEERING.md #2), just not by hand. Replacing a
scenario keeps the version you replaced.

Prove it without reading the code:

    pip install -e ".[ui]" && playwright install chromium
    pytest tests/test_builder_browser.py -v

    pytest tests/test_learner_run_browser.py -v

Chromium tests author a scenario through the UI alone, publish it, play it
as a learner in Brazil, reopen it for editing, and separately play a whole
sitting to its final score and reload halfway through to prove it resumes.
They skip loudly if Playwright is missing: a skip means unverified, not
passed.

## Try it
    curl http://127.0.0.1:8000/catalog
    # -> 2 templates x 4 locales = 8 scenarios, zero extra code

    # Start a sitting. The reply carries the run id and the scenario.
    RUN=$(curl -s -X POST http://127.0.0.1:8000/runs \
      -F template_id=heatwave_demand -F locale=nigeria -F seed=1 -F learner_id=frank \
      | python3 -c 'import sys,json; print(json.load(sys.stdin)["run"]["run_id"])')

    curl -X POST http://127.0.0.1:8000/runs/$RUN/decisions \
      -F decision_id=customer_allocation -F choice=highest_value_first -F learner_id=frank
    # -> +4.2 pts, score_so_far 100.0 (104.2 raw, clamped to 100)

    curl -X POST http://127.0.0.1:8000/runs/$RUN/decisions \
      -F decision_id=freight_choice -F choice=expedite -F learner_id=frank
    # -> -16.8 pts in Nigeria (UK: -11.8), score_so_far 87.4: the sum, not the last card

    curl -X POST http://127.0.0.1:8000/runs/$RUN/complete -F learner_id=frank
    # -> final_score, every decision with its reason, biggest_mistake, and the record

    curl "http://127.0.0.1:8000/learners/frank/progress/heatwave_demand?locale=nigeria"
    # -> runs_completed, best_run_score, current_streak, last_mistake

    curl -X POST http://127.0.0.1:8000/runs/$RUN/decisions \
      -F decision_id=freight_choice -F choice=expedite -F learner_id=frank
    # -> 409: that decision is answered and the run is already complete

    curl -X POST http://127.0.0.1:8000/runs/$RUN/decisions \
      -F decision_id=freight_choice -F choice=standard -F learner_id=mallory
    # -> 403: this run belongs to another learner

## Adding a country or an industry
Add one YAML file. config/locales/ for a country, config/templates/ for an
industry. Zero code changes — see BLUEPRINT-MAP.md and rules/ENGINEERING.md Rule 2.

You can also write the file by hand. Every option declares what it does to
the KPIs the template measures, and the weights decide how much each one
counts, so changing a weight changes the score with no code change:

    scoring:
      expedite:
        impact:
          overhead_cost:         { points: -40, scales_with: freight_expedite_multiplier }
          customer_satisfaction: { points: 12 }
        reason: "Expedite in {locale} costs {freight_expedite_multiplier}x: {delta} pts."

`scales_with` multiplies by one locale rule, which is how the same choice
scores differently per country. A `reason` may reference the locale rules,
locale, currency, choice, delta and tax_percent. Validation fails loud on an
impact naming a KPI the template does not measure, an unknown `scales_with`,
or an option with no rule at all. The older unweighted `points` form still
works for templates published before v1.0. See
config/templates/heatwave_demand.yaml.

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
See BLUEPRINT-MAP.md: it must sit ON TOP of this grounded engine, never
replace it, or it inherits Lovable's exact failure, fluent but forgetful.
As of v1.0.0 the grounding it was waiting for exists: a run records every
decision, the rule that scored it, a final score and the learner's history.
Cost it per learner-session before it ships (SCALING.md #5).
