# Parked locales

Countries that are written and tested but not shipped in this release.
The loader reads `config/locales/*.yaml` only, so a file in here is simply
not in the catalogue: no code knows the difference (ENGINEERING.md Rule 2).

Shipping one is a file move and nothing else:

    git mv config/locales/_parked/germany.yaml config/locales/
    make check

Add its numbers to `EXPECTED` in tests/test_locales.py in the same commit,
because a locale without a numeric assertion is not a supported locale
(scenarios/stages/02-localize).

| File | Why it is parked |
|------|------------------|
| `germany.yaml` | Written for v0.2. The only EU member state we have. Restore it first if funding or a pilot requires an EU locale. |
| `nigeria.yaml` | Written for v0.2. Kept because its 2.1x expedite multiplier and 45 day terms are the sharpest contrast with the UK, which makes it the best demo of the localization thesis outside the shipped pair. |
