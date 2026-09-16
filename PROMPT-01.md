# PROMPT 01 — First autonomous run: red-team, harden, and ship v0.3.0

You are working in the ERP Decision Lab repo at the current directory. Run
this task start to finish without asking questions. Where a decision is
yours to make, make it, log it in CHANGELOG.md, and keep going. Stop only
if a step below is impossible; then write what blocked you in DEBT.md and
continue with every step that does not depend on it.

## 0. Environment (do this exactly; the machine has a known trap)
The user-site Python has an Intel-only pydantic_core that fails to import
on this Apple Silicon Mac. Never use system or user-site packages.

    python3 -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]" httpx
    pytest -q                       # must report 14 passed before you touch anything
    python rules/roots/check_roots.py .   # must print "Cleared to ship"

If the repo is not a git repository, run `git init` and make an initial
commit of the untouched tree titled "v0.2.0 baseline". Every change after
that is its own commit (ENGINEERING.md #3).

## 1. Read, in this order, before changing anything
CLAUDE.md, rules/ENGINEERING.md, rules/PRODUCT.md, rules/SCALING.md,
BREAK.md, BLUEPRINT-MAP.md, ROOTS-SCORE.md, every stages/*/CONTEXT.md,
README.md. The rules win over your instincts. Rule 2 (templates x locales
are data, not code) and PRODUCT.md #6 (never claim a number the product
cannot show) are the two that most changes break.

## 2. Confirmed breaks to fix (already reproduced; do not re-argue them)
Fix in this order. Each fix = one commit = code + a contract test + a
loud-failure test (ENGINEERING.md #4). Run the full suite after each.

1. **Invalid choice is accepted and recorded.** POST /decisions/score with
   choice=TELEPORT returns 200, scores as "standard", and increments the
   learner's attempts. Validate choice against the decision's options
   from the template; return 422; never write to memory on a rejected
   request. (BREAK.md #3)
2. **Scoring rules are hardcoded in src/erpsim/scoring.py per decision id.**
   made_to_order decisions score 0 with no justification because only
   heatwave_demand ids exist in Python. This violates Rule 2: adding an
   industry currently requires editing src/. Move scoring rules into the
   template YAML (per option: base points, plus which locale_rules field
   multiplies it, if any) and make scoring.py a generic interpreter.
   heatwave_demand must produce byte-identical scores before and after
   (write the regression test first, from the current outputs). Extend
   templates.validate so a template whose options lack scoring rules
   fails loud at authoring time.
3. **Progress merges across locales.** LearnerProgress is keyed on
   learner_id + template_id; a UK attempt and a Nigeria attempt land on
   one row that still says locale=uk. Key on learner x template x locale.
   Update tutor/stages/01-recall/CONTEXT.md and the progress endpoint to
   match. Keep the frontend welcome strip working.
4. **last_mistake is never written.** memory.record_attempt accepts a
   mistake argument that main.py never passes, so ROOTS-SCORE #8 and
   PRODUCT.md #4 ("here's what tripped you up last time") are claimed but
   not delivered. On any decision with a negative score_delta, persist
   the first justification line as last_mistake and show it in the
   memory strip on return.
5. **One broken locale file takes the whole API down.** A locale YAML
   with a syntax error raises an unhandled ParserError (500) and still
   appears in /catalog. Catch it in locales.load, raise a structured
   error that maps to 404 for that locale only, exclude unparseable
   files from /catalog and /health, and log a warning naming the file.
   Same treatment for templates. Test it by writing a broken file to a
   tmp_path and pointing the loader at it; never commit a broken file.
   (BREAK.md #4)
6. **Database DSN is hardcoded.** main.py has "sqlite:///erpsim.db"
   inline (ENGINEERING.md #5, SCALING.md #1). Read ERPSIM_DATABASE_URL
   from the environment with that sqlite value as the default. Document
   the variable in README.md.
7. **Learner identity is a bare name typed into a text box.** Any name
   collides and any visitor can GET any learner's progress. Do NOT build
   auth. Do the minimum honest thing: state plainly in the UI, next to
   the name field, that progress is keyed to the name entered and is
   used only to help that learner (PRODUCT.md #7 requires this to be
   in-product, not in terms). Log the full collision problem in DEBT.md
   with repay trigger "before first external pilot".
8. **Missing per-locale numeric tests.** scenarios/stages/02-localize
   says a locale without a numeric assertion test is not supported. Only
   UK and Nigeria have one. Add one test per locale file (brazil,
   germany, uk, nigeria) asserting currency, tax_rate, and
   freight_expedite_multiplier from the YAML, so PRODUCT.md #6
   ("localized to 4 countries") is provable in pytest.
9. **Frontend gaps.** Running score in the score bar is hardcoded at
   100.0 and never updates. Errors use alert(). Replace alert() with an
   inline "Could not reach the API, retrying" state that keeps the
   in-progress scenario on screen and retries once (BREAK.md #4). Update
   the running score from each score response. No scoring or locale
   logic in JavaScript (ENGINEERING.md #6).
10. **Dead references.** README.md cites rules/RULES.md, which does not
    exist (it is rules/ENGINEERING.md). BREAK.md cites DEBT.md, which does
    not exist. Fix the link; create DEBT.md with the table columns
    Item, Found, Repay trigger, Owner.

## 3. Then run the five BREAK.md hats yourself
After the fixes, re-run each attack in BREAK.md against the app using
FastAPI's TestClient. Anything that still breaks and is not in the list
above: fix if it is under an hour of work, otherwise log it in DEBT.md.
Never leave a known break unlogged.

## 4. Release
- Bump pyproject.toml and main.py to 0.3.0.
- CHANGELOG.md: one dated entry listing every fix by number above.
- ROOTS-SCORE.md: re-score honestly. If #8 (trajectory) or #11
  (grounding) now genuinely holds, keep ROOTED and update the pointer;
  if any claim is no longer true, downgrade it and add a dated waiver.
- README.md: update the test count and the curl examples so every
  command in it works as written. Verify by running them.
- Wire the gate: add a `make check` (or scripts/check.sh) that runs
  pytest then check_roots.py and exits non-zero on either failure.
  This moves ROOTS #12 from SEEDLING toward ROOTED; update its pointer.
- Final commit "v0.3.0 — red-teamed, scoring as data, per-locale memory".

## 5. Exit criteria (all must be true or the task is not done)
- `pytest -q` passes with more tests than 14 and zero skips.
- `python rules/roots/check_roots.py .` prints "Cleared to ship".
- `pytest tests/test_generator.py::test_localization_is_not_just_translation -v` passes.
- Adding a fifth locale file and a third template file with a scoring
  block generates and scores through the API with zero src/ edits.
  Prove it in a test that writes both files to a tmp dir.
- Every curl command in README.md returns the documented status.
- DEBT.md exists and every open item has a repay trigger and an owner.

## 6. Report
Finish with a plain report: what changed (by fix number), test count
before and after, what you logged to DEBT.md and why, and the one thing
you would fix next. No hedging. If a step failed, say so with the output.

## Hard constraints
- Never touch src/ to add a country or an industry.
- Never claim in docs what a test does not prove.
- Never delete learner data or the erpsim.db of the person running this.
- Do not build the AI tutor conversation layer, multi-tenant
  infrastructure, or authentication. BLUEPRINT-MAP.md and SCALING.md #4
  say not yet, and they are right.
