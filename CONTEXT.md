# CONTEXT.md — ERP Decision Lab (L0, product level)

Every stage in this repo has a CONTEXT.md. The product did not. This is it.
CLAUDE.md routes an agent to a workspace; this file says what the product
is, what is actually true today, and what is left. Stage files own their
own contracts — this file never restates them, it points at them.

Scored 2026-09-17 against v0.4.1 (GitHub: dominicrume/ERP_LANGUAGE). Every
claim below was run, not read. The command that proves each one is named beside it.

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
**Two of those three are true today. The first is not.** See below.

---

## Who this is for

| Audience | What they need to believe | Status |
|---|---|---|
| Learner | "This taught me something about operating in Nigeria." | Partly — decisions teach, the run never concludes |
| Instructor | "I can write my own scenario without an engineer." | True as of v0.4.0, browser-proven |
| Buyer / funder | "Localization is real business logic, not a UI skin." | True and demonstrable in one command |

---

## The map

| Layer | Where | State |
|---|---|---|
| API | `src/erpsim/main.py` | 11 endpoints, all reachable |
| Scenario engine | `generator.py`, `templates.py`, `locales.py` | Deterministic per seed |
| Scoring | `scoring.py` | Interpreter over template data. **Per-decision only** |
| Learner memory | `memory.py` | SQLModel, keyed learner × template × locale |
| Authoring | `authoring.py` | Draft → validate → preview → publish |
| Frontend | `static/index.html` (single file, tokens, light + dark) | Learner view + instructor builder |
| Database | SQLite via `ERPSIM_DATABASE_URL` | **No migration tooling** |
| Gate | `scripts/check.sh` / `make check` | pytest + ROOTS, non-zero on failure |

Content that grows without code: `config/locales/*.yaml` (4 countries),
`config/templates/*.yaml` (2 industries). 2 × 4 = 8 playable combinations.

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

123 tests. `make check` is green.

---

## What is BROKEN (each reproduced on 2026-09-17)

These are not opinions. The probe output is in the session that wrote this file.

**A. "Running score" does not run. — P0, the product lies on screen.**
Each decision is scored independently as `100 + points`. Score decision one
(+8) and the API says 108. Score decision two (−32) and it says 68, not 76.
Until v0.4.1 the score bar labelled this "Running score"; it now honestly
says "Latest decision score", but the model underneath is still per-decision. A learner
who makes two decisions is shown a number that silently discards the first.
`src/erpsim/scoring.py` line ~44 returns `base = 100.0 + points`.

**B. "Attempts" counts decisions, not runs. — P0, the memory strip misleads.**
One learner, one scenario, two decisions, and the record says `attempts=2`,
`best_score=108.0`. `best_score` is therefore the best *single decision*
ever made, not the best run — and it can exceed 100, which is meaningless
to a learner. Since v0.4.1 the welcome strip says so honestly ("you have
made 2 decisions ... best single decision"), but there is still no record of
a completed sitting to show.

**C. `kpi_weights` is dead data. — P1, the product is hollow where it matters.**
Every template declares what it measures and the weights are validated to
sum to 1.0. `grep -rn kpi_weights src/erpsim/` shows they are shipped in
the scenario payload and **never multiply anything**. Change any weight and
no score moves. For a decision-support trainer this is the centre of the
product, and it is inert.

**D. A scenario never finishes. — P0.**
There is no session id, no `/scenarios/complete`, no final score, no
summary. A learner turns over the cards and the screen simply stops.
Nothing tells them how they did overall or what to do next.

**E. No streak. — P1, PRODUCT.md #4 names it explicitly.**
Nothing in the data model or the frontend tracks one. PRODUCT.md #4 requires
"a visible best-score, a streak, and an honest 'here's what tripped you up'".
Two of three exist.

**F. No database migration path. — P1, first deploy hazard.**
`SQLModel.metadata.create_all()` creates missing tables and nothing else.
Proven: seeding a pre-v0.3 database and starting v0.4 leaves the v0.3
indexes uncreated. It happens to work today only because the column set did
not change. The next schema change to `LearnerProgress` silently corrupts or
ignores existing learner data. There is no Alembic, no versioning, no
`scripts/migrate`.

**G. No unique constraint on the learner record. — P2, latent.**
`LearnerProgress` indexes `learner_id`, `template_id` and `locale`
separately but has no `UNIQUE` across the three. `record_attempt` does a
read-then-write with no constraint behind it, and `recall` takes `.first()`.
Under SQLite's serialization I could not reproduce a duplicate, so this is a
latent risk rather than a live bug — but it becomes real on Postgres
(SCALING.md #1), where two requests can genuinely interleave, and the
second row would be invisible to every later read.

**H. The learner is never shown what is being measured. — P2.**
`kpi_weights` never reaches the learner's screen. They are scored against
priorities they cannot see.

---

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

1. **Make a run a real thing** (gaps A, B, D). A scenario run gets an id,
   accumulates decisions, and completes with a final score. Memory keys on
   completed runs. This unblocks everything else, including the tutor layer.
2. **Make `kpi_weights` load-bearing** (gaps C, H). An option's impact is
   expressed per KPI; the final score is the weighted sum; the learner sees
   the breakdown. This is what makes it decision-*support* training.
3. **Streak and honest progress** (gap E).
4. **Schema versioning** (gaps F, G) before anyone's data matters.
5. **Repay DEBT.md** in its stated trigger order.

`PROMPT-02.md` is the autonomous brief for exactly this, with exit criteria.

---

## Run it

    python3 -m venv .venv && source .venv/bin/activate
    pip install -e ".[ui]" && playwright install chromium
    make check                                  # 110 tests + ROOTS gate
    uvicorn erpsim.main:app --reload --app-dir src
    # http://127.0.0.1:8000

On this machine the user-site Python has an Intel-only `pydantic_core` that
will not import on Apple Silicon. Always use the venv.

## Rules that outrank any judgement call
`rules/ENGINEERING.md`, `rules/PRODUCT.md`, `rules/SCALING.md`, `BREAK.md`.
Read them before changing anything. Rule 2 (templates × locales are data,
never code) and PRODUCT.md #6 (never claim a number the product cannot show)
are the two that most changes break.
