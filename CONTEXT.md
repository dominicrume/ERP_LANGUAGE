# CONTEXT.md — ERP Decision Lab (L0, product level)

Every stage in this repo has a CONTEXT.md. The product did not. This is it.
CLAUDE.md routes an agent to a workspace; this file says what the product
is, what is actually true today, and what is left. Stage files own their
own contracts — this file never restates them, it points at them.

Scored 2026-09-18 against v1.0.0 (GitHub: dominicrume/ERP_LANGUAGE). Every
claim below was run, not read. The command that proves each one is named
beside it, and the same gate runs on every push.

---

## Input
A learner's operational decision, inside a story, under one country's rules.
An instructor's scenario, authored in plain language.

## Process
`template × locale = scenario`. Templates are one YAML file per industry,
locales one YAML file per country. A deterministic interpreter scores each
decision against the locale's own numbers and returns the reason it used.
No LLM call is involved in scoring, by design (SCALING.md #5).

## Output
A scored decision with its provenance, and a learner record that survives
the session.

## Completion (product level)
A learner can finish a scenario and be told how they did, an instructor can
author one without an engineer, and a buyer can watch the same scenario
behave differently in four countries on demand.
**All three are true as of v1.0.0.** What is left is in the last section.

---

## Who this is for

| Audience | What they need to believe | Status |
|---|---|---|
| Learner | "This taught me something about operating in Brazil." | True: a sitting starts, accumulates and ends with a score and a reason for each decision |
| Instructor | "I can write my own scenario without an engineer." | True as of v0.4.0, browser-proven; authors KPI impacts as of v1.0.0 |
| Buyer / funder | "Localization is real business logic, not a UI skin." | True and demonstrable in one command |

---

## The map

| Layer | Where | State |
|---|---|---|
| API | `src/erpsim/main.py` | 11 endpoints, all reachable |
| Scenario engine | `generator.py`, `templates.py`, `locales.py` | Deterministic per seed |
| Scoring | `scoring.py` | Interpreter over template data, weighted by the template's own KPIs |
| Sittings | `runs.py` | A run: starts, accumulates, completes with a final score |
| Learner memory | `memory.py` | Completed runs, best run, streak, keyed learner × template × locale |
| Schema | `migrations.py` | Numbered migrations, version table, applied at startup |
| Authoring | `authoring.py` | Draft → validate → preview → publish |
| Frontend | `static/index.html` (single file, tokens, light + dark) | Learner view + instructor builder |
| Database | SQLite via `ERPSIM_DATABASE_URL` | Versioned, unique per learner × template × locale |
| Gate | `scripts/check.sh` / `make check` | migrations + pytest + ROOTS, also on every push (GitHub Actions) |

Content that grows without code: `config/locales/*.yaml` and
`config/templates/*.yaml`. This release ships Brazil and the UK against 2
industries, so 2 × 2 = 4 playable combinations. Germany and Nigeria are
written and parked in `config/locales/_parked`; restoring one is a file move
(`tests/test_locales.py` proves it).

---

## What is DONE (verified, not claimed)

| # | Capability | Proof |
|---|---|---|
| 1 | Localization is numeric, not translated | `pytest tests/test_generator.py::test_localization_is_not_just_translation` |
| 2 | A new country or industry needs zero `src/` changes | `pytest tests/test_zero_code_growth.py` |
| 3 | Scoring rules live in template data, not Python | `pytest tests/test_scoring.py` |
| 4 | Every score carries the locale rule that produced it | `tests/test_scoring.py::test_every_option_of_every_template_scores_with_a_reason` |
| 5 | Invalid choice / decision / id rejected, nothing recorded | `pytest tests/test_api.py` |
| 6 | One broken config file 404s for itself only | `pytest tests/test_broken_config.py` |
| 7 | Learner memory never merges across learners or locales | `pytest tests/test_memory.py` |
| 8 | Instructor authors and publishes without seeing YAML | `pytest tests/test_builder_browser.py` (needs `.[ui]`) |
| 9 | Frontend computes no score or locale logic | `pytest tests/test_frontend_contract.py` |
| 10 | DSN is runtime config, SQLite → Postgres by swap | `pytest tests/test_config.py` |
| 11 | Authored text can never run as script for a learner | `tests/test_builder_browser.py::test_authored_text_can_never_run_as_script_in_a_learners_browser` |
| 12 | Contrast, layout, focus and touch targets hold in light and dark, desktop and phone | `pytest tests/test_ui_quality_browser.py` |
| 13 | A sitting starts, accumulates and finishes, and the score is the sum of its decisions | `pytest tests/test_runs.py` |
| 14 | A learner plays a whole scenario in a browser and is told how they did | `pytest tests/test_learner_run_browser.py` |
| 15 | Changing a KPI weight in the YAML changes the score, with no code change | `pytest tests/test_kpi_weighting.py` |
| 16 | A record counts finished sittings, with a streak that survives month and year ends | `pytest tests/test_memory.py` |
| 17 | A seeded v0.4 database upgrades with the learner's data intact | `pytest tests/test_migrations.py` |
| 18 | Nobody plays in another learner's sitting, answers twice, or finishes early | `pytest tests/test_runs.py -k "cannot or another"` |

202 tests. `make check` is green locally and on GitHub Actions.

---

## What is BROKEN

Nothing in the learner or instructor path that I can reproduce. The eight
defects this file recorded on 2026-09-17 (A to H) are closed and each has a
test named above. What is left is deliberate deferral, recorded in DEBT.md
and summarised next, plus these honest limits:

- **A score above 100 is clamped, not banked.** A generous run can exceed
  100 internally; the learner is shown 100 and the raw total sits beside it
  in the API. If that ever needs to read differently, change `runs.clamp`.
- **Scores changed at v1.0.0.** KPI weighting moved every number. A learner
  who played before the change cannot compare their old best with a new one.
  The old goldens are kept so the change stays visible, not silent.
- **Abandoned sittings are never cleaned up.** Harmless at demo scale,
  unbounded over a term (DEBT.md).

## What is NOT BUILT (and whether that is correct)

| Item | Correct to defer? | Trigger |
|---|---|---|
| AI tutor conversation layer | **Yes** — BLUEPRINT-MAP.md is right that it must sit on top of a grounded engine | After the engine concludes a run (gap D) |
| Learner accounts / auth | Yes for a local demo | Before first external pilot (DEBT.md) |
| Authenticated publishing | Yes for a local demo | Before hosting anywhere a learner can reach |
| Locale authoring surface | Yes, for now | When a prospect asks for a country we do not ship |
| Multi-tenant isolation | **Yes** — SCALING.md #4, do not build speculatively | Second paying institution |
| Hosted CI | No, this is just undone | Before first external pilot |

---

## What is LEFT, in the order it should be done

1. **Identity.** A learner is still just a typed name, and anyone can read
   anyone's record or publish a scenario. This is the one thing that blocks
   hosting the app anywhere a cohort can reach it.
2. **Locale authoring.** A country is still a hand-written YAML file. The
   day a prospect asks for a country we do not ship, this becomes urgent.
3. **The AI tutor layer.** Now unblocked: a run records every decision, its
   reason and a final score, which is exactly the grounding BLUEPRINT-MAP.md
   said the chat layer must sit on top of. Cost it per learner-session
   before it ships (SCALING.md #5).
4. **Housekeeping.** Abandoned runs, and retiring the deprecated stateless
   scoring endpoint once nothing calls it.

## Run it

    python3 -m venv .venv && source .venv/bin/activate
    pip install -e ".[ui]" && playwright install chromium
    make check                                  # migrations + 202 tests + ROOTS gate
    uvicorn erpsim.main:app --reload --app-dir src
    # http://127.0.0.1:8000

On this machine the user-site Python has an Intel-only `pydantic_core` that
will not import on Apple Silicon. Always use the venv.

## Rules that outrank any judgement call
`rules/ENGINEERING.md`, `rules/PRODUCT.md`, `rules/SCALING.md`, `BREAK.md`.
Read them before changing anything. Rule 2 (templates × locales are data,
never code) and PRODUCT.md #6 (never claim a number the product cannot show)
are the two that most changes break.
