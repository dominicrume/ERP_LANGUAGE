# PROMPT 02 — Build ERP Decision Lab to v1.0, autonomously

You are working in the ERP Decision Lab repo at the current directory. Run
this start to finish without asking questions. Where a decision is yours,
make it, record it in CHANGELOG.md, and keep going. If a step is genuinely
impossible, write why in DEBT.md with a repay trigger and continue with
every step that does not depend on it. Report honestly at the end.

Read `CONTEXT.md` first. It is the verified status as of v0.4.0 and it
names every gap below with the evidence that produced it. Do not re-litigate
those findings; they were reproduced against a running server.

## 0. Environment (the machine has a known trap)
The user-site Python has an Intel-only `pydantic_core` that will not import
on this Apple Silicon Mac. Never use system or user-site packages.

    python3 -m venv .venv && source .venv/bin/activate
    pip install -e ".[ui]" && playwright install chromium
    make check          # MUST print 110 passed, then "Cleared to ship"

If that is not green, stop and fix it before touching anything else. Every
change after that is its own commit (ENGINEERING.md #3).

## 1. Read before changing anything
`CONTEXT.md`, `rules/ENGINEERING.md`, `rules/PRODUCT.md`, `rules/SCALING.md`,
`BREAK.md`, `DEBT.md`, `BLUEPRINT-MAP.md`, `ROOTS-SCORE.md`, every
`*/stages/*/CONTEXT.md`. The rules outrank your instincts. The two most
easily broken: Rule 2 (templates × locales are data, never code) and
PRODUCT.md #6 (never claim a number the product cannot show working).

---

## 2. The work, in dependency order

Each numbered item is one commit: contract test + loud-failure test + code
+ any CONTEXT.md whose contract you changed. Run `make check` after each.

### 1 — A scenario run is a real object (fixes CONTEXT.md gaps A, B, D)

This is the keystone. Everything else depends on it.

- New model `ScenarioRun`: `id` (uuid string), `learner_id`, `template_id`,
  `locale`, `seed`, `started_at`, `completed_at` (nullable), `final_score`
  (nullable). New model `RunDecision`: `run_id`, `decision_id`, `choice`,
  `score_delta`, `justification`, `decided_at`.
- `POST /runs` starts a run from `template_id + locale + seed + learner_id`
  and returns the run id and the scenario payload.
- `POST /runs/{run_id}/decisions` records one decision and returns the
  decision result **plus the true cumulative score so far**.
- A decision already answered in that run is rejected with 409, not
  silently re-scored. A decision not in the scenario is 422. A run that is
  already complete rejects further decisions with 409.
- `POST /runs/{run_id}/complete` is refused with 422 until every decision
  in the scenario has been answered. On success it stores `final_score` and
  `completed_at` and returns the full summary.
- `GET /runs/{run_id}` returns the run, its decisions and its state.
- Keep `POST /decisions/score` working exactly as it does now, marked
  deprecated in its docstring. It is the stateless preview path the
  instructor builder uses. Do not break `tests/test_api.py`.
- **`running_score` must never again be returned for a multi-decision
  scenario without being cumulative.** Write the test that proves
  decision one (+8) then decision two (−32) yields 76, not 68.

### 2 — `kpi_weights` becomes load-bearing (fixes gaps C, H)

Today every template declares what it measures and the weights multiply
nothing. Make them the spine of the score.

- Extend the option schema so an option states its impact per KPI:

      scoring:
        expedite:
          impact:
            cash_position:         { points: -20, scales_with: freight_expedite_multiplier }
            customer_satisfaction: { points: 10 }
          reason: "Expedite in {locale} costs {freight_expedite_multiplier}x: {delta} pts."

- A decision's contribution is `Σ over KPIs (impact_points × kpi_weight)`.
  The run's final score is `100 + Σ decisions`, clamped to 0–100 and
  rounded to one decimal. A score above 100 is meaningless to a learner.
- `templates.validate` must reject: an `impact` naming a KPI not in
  `kpi_weights`; a `scales_with` that is not a locale rule field; an option
  with neither `points` nor `impact`.
- **Keep the legacy `points` form working.** An option with bare `points`
  contributes that many points to the run total unweighted. Both shipped
  templates must be migrated to `impact` in this same commit so the model
  is not half-applied, but the legacy path stays supported and tested,
  because an instructor may have published a template already.
- `tests/fixtures/heatwave_scores_v0.2.json` pins the old per-decision
  numbers. Those numbers change under the weighted model. **Do not delete
  it silently.** Rename it to `heatwave_scores_v0.2_legacy.json`, keep it
  asserting the legacy `points` path, and add a new v1.0 golden for the
  weighted path. Explain the change in CHANGELOG.md.
- The learner must see what is being measured: show the KPI weights on the
  scenario card, and show the per-KPI breakdown on completion.

### 3 — Completion, streak and honest progress (fixes gap E)

- `LearnerProgress` now records completed runs: `runs_completed`,
  `best_score` (best completed run, ≤100), `last_mistake`,
  `current_streak`, `longest_streak`, `last_completed_on` (date).
- Streak rule, stated in-product so it is never a mystery: a streak is
  consecutive **calendar days** on which the learner completed at least one
  run. Completing two runs in one day does not raise it; missing a day
  resets `current_streak` to 1 on the next completion. Test the boundary
  cases: same day, next day, two days later, across a month end.
- Migrate the old per-decision `attempts` column to `runs_completed`
  honestly — do not pretend historical decision counts were runs. Set
  `runs_completed = 0` for pre-v1.0 rows and note it in CHANGELOG.md.
- The welcome strip shows best score, streak, and what tripped them up.

### 4 — Schema versioning (fixes gaps F, G)

- Add Alembic (or, if you judge it lighter, a versioned migration module
  under `src/erpsim/migrations/` with an explicit `schema_version` table).
  Whichever you choose, it must: detect the current version, apply ordered
  migrations, be idempotent, and refuse to run against a newer schema than
  it knows.
- Ship the migration that takes a v0.4 database to v1.0 (the new tables and
  the `LearnerProgress` column changes). Test it by seeding a real v0.4
  database, migrating it, and asserting the learner's data survived.
- Add `UNIQUE (learner_id, template_id, locale)` to `LearnerProgress` and
  make `record_attempt` an upsert that cannot create a second row.
- `make check` must run migrations against a temp database as part of the
  gate. `scripts/migrate.sh` (or `make migrate`) applies them for real.

### 5 — Instructor builder catches up (do not let the UI fall behind the model)

- The builder must author `impact` per KPI, not a single points box. The
  KPI list the instructor defines in "What it measures" becomes the set of
  impacts each option can move. Keep it plain language: no instructor ever
  sees the words `impact`, `scales_with` or `kpi_weights`.
- The cross-locale preview must show the **run-level** outcome, not just
  per-decision deltas: pick the best and worst path through the scenario in
  each country and show the final scores. That is the instructor seeing
  their own scenario's real range.
- The browser suite must still pass and must gain a test that authors a
  KPI-weighted scenario and plays it to completion.

### 6 — Frontend and UX, wired properly end to end

- The learner flow becomes: choose → play a run → each card flips with its
  reason and the **true cumulative score** → a completion card with the
  final score, the per-KPI breakdown, the single biggest mistake, and a
  "play it in another country" button that starts a new run on the same
  template.
- Fix the accessibility gaps I found: no `<main>` landmark, no `<label for>`
  on the learner name field, no focus management when the completion card
  appears. Add them. Keep the existing `prefers-reduced-motion` handling.
- Keep the honest reconnecting strip and the one retry. A dropped
  connection mid-run must not lose the run — it is server-side now, so
  reload and resume must work. Test that.
- No scoring or locale arithmetic in JavaScript. `tests/test_frontend_contract.py`
  already enforces this; keep it passing.

### 7 — Wire the gate for real

- GitHub Actions workflow running `make check` on push and PR, including
  the browser suite. The repo has no remote yet, so the workflow lands
  unused — say so plainly in DEBT.md rather than claiming CI exists.
- Close the DEBT.md row for hosted CI only if a remote genuinely exists.

---

## 3. Then attack it (BREAK.md, all five hats)

Re-run every hat against the finished build with a real TestClient and a
real browser. Pay particular attention to:

- **Thief:** can a learner POST decisions to *another learner's* run? Can
  they complete a run they did not start? Can they replay a decision to
  farm a better score? Can they forge a run id? Each must be a clean 403 or
  409, tested.
- **Firefighter:** kill the connection mid-run and reload. The learner must
  resume, not lose the run.
- **Doubter:** is the streak rule one a university would accept, or does it
  punish a learner who studies twice a week? Write your answer in
  CHANGELOG.md; change the rule if the honest answer is that it punishes.

Anything still broken and not listed above: fix it if it is under an hour,
otherwise log it in DEBT.md with a repay trigger. Never leave a known break
unlogged.

## 4. Release

- Bump to 1.0.0 in `pyproject.toml` and `main.py`.
- CHANGELOG.md: one dated entry, every item above by number, and an
  explicit note on the golden-fixture change and the `attempts` migration.
- ROOTS-SCORE.md: re-score honestly. #8 trajectory and #11 grounding should
  strengthen; #12 CI/CD only moves if a remote exists. Downgrade anything
  that is no longer true and date the waiver.
- CONTEXT.md: rewrite the DONE / BROKEN / LEFT sections against the new
  reality. **This file is the contract that the next person inherits — if
  it overstates by one line, the whole document stops being trustworthy.**
- README.md: update the test count and make every command in it work as
  written. Verify by running them against a live server, not by reading.
- Final commit `v1.0.0 — runs, weighted KPIs, streaks, migrations`.

## 5. Exit criteria (all must hold, or the task is not done)

- `make check` green, more tests than 110, zero skips other than the
  browser suite when Playwright is genuinely absent.
- A learner can start a run, answer every decision, complete it, and see a
  final score that equals `100 + Σ weighted impacts`, clamped to 0–100.
  Proven end to end in Chromium.
- Two decisions of +8 and −32 yield 76. Proven by test.
- Changing a `kpi_weight` in a template YAML changes the final score, with
  no `src/` edit. Proven by test.
- A fifth locale and a third industry still need zero `src/` changes.
  `tests/test_zero_code_growth.py` must still pass, updated for the new model.
- A seeded v0.4 database migrates to v1.0 with learner data intact. Proven.
- Streak boundaries proven: same day, consecutive days, a skipped day, a
  month boundary.
- Every curl command in README.md returns the documented status against a
  live server.
- DEBT.md: every open row has a repay trigger and an owner.

## 6. Report

Finish with a plain report: what changed by item number, test count before
and after, what you logged to DEBT.md and why, every judgement call you
made (especially the streak rule and the golden fixture), and the one thing
you would do next. If a step failed, say so and show the output. Do not
describe work you did not finish as finished.

## Hard constraints

- Never touch `src/` to add a country or an industry.
- Never claim in docs what a test does not prove.
- Never delete or migrate away a learner's data without a test that proves
  it survived, and never delete the operator's `erpsim.db`.
- Do not build the AI tutor conversation layer, multi-tenant infrastructure,
  or authentication. BLUEPRINT-MAP.md and SCALING.md #4 say not yet, and
  they are right. The run object you are building in item 1 is the
  precondition the tutor layer has been waiting for — leave it clean.
