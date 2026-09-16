# Stage: Localization Rules (the thesis)
## Input: a locale code
## Process: load config/locales/{code}.yaml — currency, tax type/rate,
  freight multiplier, payment terms. NEW COUNTRY = NEW FILE, NEVER NEW CODE.
## Output: locale_rules dict merged into every scenario for that country
## Completion: tested per-locale (Rule 6) — a locale without a numeric
  assertion test is not a supported locale.
