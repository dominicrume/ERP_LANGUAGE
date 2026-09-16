# BREAK.md — How We Attack This Product Before Anyone Else Does

Standing KYA Step 2 (Attack). Before any release, run these five hats
against the current build. Fix what breaks. Log what you can't fix yet
in DEBT.md with a repay trigger — never ship an unlogged known break.

## 1 — The Planner: is the shape even right?
- Does the localization thesis (test_localization_is_not_just_translation)
  still pass after the last change? If a "locale" now only swaps currency
  symbols, the product has quietly become the thing it was built to beat.
- Does adding one template x one locale still require ZERO src/ changes?
  If not, Rule 2 (ENGINEERING.md) has been violated — stop and fix first.

## 2 — The Builder: can this actually be shipped this week?
- Can an instructor with no coding background author a valid template
  through the UI alone, today? If the honest answer needs a YAML tutorial,
  the authoring flow (PRODUCT.md #5) is not built, only stubbed.

## 3 — The Thief: how would someone abuse or break this?
- Submit a decision for a template/locale combination that doesn't exist —
  does it 404 cleanly, or does it silently generate garbage?
- Hammer /decisions/score with the same learner_id and a bad choice value —
  does memory.py record corrupt progress, or reject and log it?
- Can one learner's learner_id collide with another's (name reuse) and
  merge their progress? (Rule: PRODUCT.md #7 — this is a trust breach, not
  a bug, if it happens.)

## 4 — The Firefighter: what fails at 3AM during a live pitch demo?
- Locale file has a YAML typo — does the WHOLE API 500, or does only that
  one locale 404 while the others keep working? (It must be the latter.)
- Frontend loses connection to the API mid-scenario — does the learner see
  a broken card, or an honest "reconnecting" state that doesn't lose their
  in-progress decision?

## 5 — The Doubter: what are we assuming that might not be true?
- We assume Frank's Friday MVP audience and this funding-pitch audience
  want the SAME product. Confirm before combining messaging.
- We assume "localization" as tax/freight rules is what buyers mean by
  the word. A university procurement officer may mean UI language only —
  test the pitch language on one real prospect before printing it on a deck.
- We assume static-file frontend + FastAPI is enough for a funding demo.
  It is NOT yet enough for 50 concurrent university users — that's the
  next scaling gate (SCALING.md #4), not a Friday problem.
