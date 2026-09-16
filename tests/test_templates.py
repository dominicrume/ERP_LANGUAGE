import pytest
from erpsim import templates


def test_valid_template_passes():
    templates.validate({
        "id": "x", "industry": "y", "title": "t", "narrative": "n",
        "product_pool": ["a"], "decisions": [{"id": "d", "label": "l", "options": ["a"]}],
        "kpi_weights": {"a": 1.0},
    })


def test_kpi_weights_must_sum_to_one():
    with pytest.raises(templates.InvalidTemplateError):
        templates.validate({
            "id": "x", "industry": "y", "title": "t", "narrative": "n",
            "product_pool": ["a"], "decisions": [{"id": "d", "label": "l", "options": ["a"]}],
            "kpi_weights": {"a": 0.5},
        })


def test_missing_key_fails_loud():
    with pytest.raises(templates.InvalidTemplateError):
        templates.validate({"id": "x"})
