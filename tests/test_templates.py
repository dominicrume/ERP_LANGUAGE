import pytest
from erpsim import templates


def _tpl(**overrides):
    base = {
        "id": "x", "industry": "y", "title": "t", "narrative": "n",
        "product_pool": ["a"],
        "decisions": [{"id": "d", "label": "l", "options": ["a", "b"],
                       "scoring": {"a": {"points": 5, "reason": "good: {points:+d}"},
                                   "b": {"points": -10, "multiply_by": "freight_expedite_multiplier",
                                         "reason": "bad in {locale}: {points:.1f}"}}}],
        "kpi_weights": {"a": 1.0},
    }
    base.update(overrides)
    return base


def test_valid_template_passes():
    templates.validate(_tpl())


def test_kpi_weights_must_sum_to_one():
    with pytest.raises(templates.InvalidTemplateError):
        templates.validate(_tpl(kpi_weights={"a": 0.5}))


def test_missing_key_fails_loud():
    with pytest.raises(templates.InvalidTemplateError):
        templates.validate({"id": "x"})


def test_decision_without_scoring_fails_loud():
    """Fix 2: an option with no scoring rule cannot be published (Rule 7)."""
    d = _tpl()["decisions"][0]
    d["scoring"].pop("b")
    with pytest.raises(templates.InvalidTemplateError, match="no scoring rule for options \\['b'\\]"):
        templates.validate(_tpl(decisions=[d]))


def test_scoring_for_unknown_option_fails_loud():
    d = _tpl()["decisions"][0]
    d["scoring"]["zzz"] = {"points": 1, "reason": "r"}
    with pytest.raises(templates.InvalidTemplateError, match="unknown options"):
        templates.validate(_tpl(decisions=[d]))


def test_multiply_by_must_be_a_locale_rule_field():
    d = _tpl()["decisions"][0]
    d["scoring"]["b"]["multiply_by"] = "moon_phase"
    with pytest.raises(templates.InvalidTemplateError, match="multiply_by"):
        templates.validate(_tpl(decisions=[d]))


def test_reason_may_only_reference_known_fields():
    d = _tpl()["decisions"][0]
    d["scoring"]["a"]["reason"] = "hello {nonexistent}"
    with pytest.raises(templates.InvalidTemplateError, match="unknown fields"):
        templates.validate(_tpl(decisions=[d]))


def test_points_must_be_numeric():
    d = _tpl()["decisions"][0]
    d["scoring"]["a"]["points"] = "lots"
    with pytest.raises(templates.InvalidTemplateError, match="numeric 'points'"):
        templates.validate(_tpl(decisions=[d]))


def test_shipped_templates_all_validate():
    for t in templates.available():
        templates.load(t)
