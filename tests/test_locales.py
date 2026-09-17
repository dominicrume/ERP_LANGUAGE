"""scenarios/stages/02-localize completion clause: a locale without a
numeric assertion test is not a supported locale. One test per country,
asserting the actual numbers — so PRODUCT.md #6 ("localized to 4
countries") is provable, not claimed."""
import pytest
from erpsim import generator, locales

# currency, tax type, standard tax rate, expedite multiplier, payment terms
EXPECTED = {
    "uk":      ("UK", "GBP", "VAT",      0.20,  1.6, 30),
    "germany": ("DE", "EUR", "VAT",      0.19,  1.5, 14),
    "nigeria": ("NG", "NGN", "VAT",      0.075, 2.1, 45),
    "brazil":  ("BR", "BRL", "ICMS_ISS", 0.18,  1.9, 28),
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


def test_four_locales_give_four_distinct_expedite_outcomes():
    """PRODUCT.md #6: 'localized to 4 countries' must mean 4 distinct,
    correct outcomes on demand — not 4 currency symbols."""
    from erpsim import scoring
    deltas = {l: scoring.score_decision(generator.generate("heatwave_demand", l, 1),
                                        "freight_choice", "expedite")["score_delta"]
              for l in EXPECTED}
    assert len(set(deltas.values())) == 4, deltas
