"""Core thesis tests: template x locale, zero code changes needed per pair."""
import pytest
from erpsim import generator, locales, templates


def test_all_template_locale_pairs_generate():
    """N templates x M locales must all generate — that ratio IS the product."""
    for t in templates.available():
        for l in locales.available():
            s = generator.generate(t, l, seed=1)
            assert s["locale"] and s["narrative"]


def test_same_seed_is_deterministic():
    a = generator.generate("heatwave_demand", "uk", seed=42)
    b = generator.generate("heatwave_demand", "uk", seed=42)
    assert a == b


def test_unknown_locale_fails_loud():
    with pytest.raises(locales.UnknownLocaleError):
        generator.generate("heatwave_demand", "atlantis", seed=1)


def test_unknown_template_fails_loud():
    with pytest.raises(templates.UnknownTemplateError):
        generator.generate("nonexistent", "uk", seed=1)


def test_localization_is_not_just_translation():
    """The same template through two locales must carry DIFFERENT numeric
    rules — proving this is localization, not a language swap."""
    uk = generator.generate("heatwave_demand", "uk", seed=1)
    ng = generator.generate("heatwave_demand", "nigeria", seed=1)
    assert uk["locale_rules"]["tax_rate"] != ng["locale_rules"]["tax_rate"]
    assert uk["currency"] != ng["currency"]
    assert uk["locale_rules"]["freight_expedite_multiplier"] != ng["locale_rules"]["freight_expedite_multiplier"]
