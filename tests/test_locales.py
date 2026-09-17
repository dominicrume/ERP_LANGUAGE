"""scenarios/stages/02-localize completion clause: a locale without a
numeric assertion test is not a supported locale. One test per country,
asserting the actual numbers — so PRODUCT.md #6 ("localized to 4
countries") is provable, not claimed."""
import shutil
from pathlib import Path

import pytest
from erpsim import generator, locales, scoring

# currency, tax type, standard tax rate, expedite multiplier, payment terms
EXPECTED = {
    # This release ships Brazil and the UK. Parked countries keep their own
    # numbers in config/locales/_parked and rejoin this table when restored.
    "brazil":  ("BR", "BRL", "ICMS_ISS", 0.18,  1.9, 28),
    "uk":      ("UK", "GBP", "VAT",      0.20,  1.6, 30),
}


def test_every_shipped_locale_has_a_numeric_assertion():
    assert set(locales.available()) == set(EXPECTED), \
        "a locale file without a row in EXPECTED is not a supported locale"


@pytest.mark.parametrize("locale_id", sorted(EXPECTED))
def test_locale_numbers(locale_id):
    code, currency, tax_type, tax_rate, expedite, terms = EXPECTED[locale_id]
    s = generator.generate("heatwave_demand", locale_id, seed=1)
    assert s["locale"] == code
    assert s["locale_id"] == locale_id
    assert s["currency"] == currency
    r = s["locale_rules"]
    assert r["tax_type"] == tax_type
    assert r["tax_rate"] == pytest.approx(tax_rate)
    assert r["freight_expedite_multiplier"] == pytest.approx(expedite)
    assert r["payment_terms_days"] == terms


def test_every_shipped_locale_gives_a_distinct_expedite_outcome():
    """PRODUCT.md #6: 'localized to N countries' must mean N distinct,
    correct outcomes on demand, not N currency symbols."""
    deltas = {l: scoring.score_decision(generator.generate("heatwave_demand", l, 1),
                                        "freight_choice", "expedite")["score_delta"]
              for l in EXPECTED}
    assert len(set(deltas.values())) == len(EXPECTED), deltas


# ---- what this release ships, and how it expands ----

PARKED = Path(__file__).resolve().parents[1] / "config" / "locales" / "_parked"


def test_this_release_ships_brazil_and_the_uk():
    """Narrowing the catalogue is a product decision, so it is asserted
    rather than left to whatever files happen to be in the folder."""
    assert locales.available() == ["brazil", "uk"]


def test_parked_countries_are_kept_not_deleted():
    parked = sorted(p.stem for p in PARKED.glob("*.yaml"))
    assert parked == ["germany", "nigeria"]


def test_restoring_a_parked_country_needs_no_code_change(tmp_path, monkeypatch):
    """The expansion pitch, proven: a country rejoins the catalogue by moving
    one file. Nothing in src/ mentions it (ENGINEERING.md Rule 2)."""
    shipped = tmp_path / "locales"
    shutil.copytree(locales._DIR, shipped, ignore=shutil.ignore_patterns("_parked"))
    shutil.copy(PARKED / "germany.yaml", shipped / "germany.yaml")
    monkeypatch.setattr(locales, "_DIR", shipped)

    assert locales.available() == ["brazil", "germany", "uk"]
    s = generator.generate("heatwave_demand", "germany", seed=1)
    assert s["currency"] == "EUR" and s["locale_rules"]["tax_rate"] == 0.19
    r = scoring.score_decision(s, "freight_choice", "expedite")
    assert r["score_delta"] == -10.8            # -40 x 1.5 x 0.25, plus 12 x 0.35

    src = Path(__file__).resolve().parents[1] / "src" / "erpsim"
    for py in src.glob("*.py"):
        assert "germany" not in py.read_text().lower(), py.name
