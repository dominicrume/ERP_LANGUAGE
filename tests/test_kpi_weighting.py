"""CONTEXT.md gap C: kpi_weights used to be validated, shipped and then
ignored. An instructor could move a weight from 40% to 90% and no score
changed. These tests make the weights load-bearing and keep them that way.
"""
import shutil

import pytest
import yaml

from erpsim import generator, locales, scoring, templates


@pytest.fixture
def sandbox_templates(tmp_path, monkeypatch):
    d = tmp_path / "templates"
    shutil.copytree(templates._DIR, d)
    monkeypatch.setattr(templates, "_DIR", d)
    return d


def _reweight(sandbox, template_id, weights):
    path = sandbox / f"{template_id}.yaml"
    data = yaml.safe_load(path.read_text())
    data["kpi_weights"] = weights
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _delta(template_id, locale, decision_id, choice):
    s = generator.generate(template_id, locale, seed=1)
    return scoring.score_decision(s, decision_id, choice)["score_delta"]


def test_changing_a_weight_changes_the_score_with_no_code_change(sandbox_templates):
    before = _delta("heatwave_demand", "uk", "freight_choice", "expedite")
    _reweight(sandbox_templates, "heatwave_demand",
              {"cash_position": 0.05, "customer_satisfaction": 0.05, "overhead_cost": 0.90})
    after = _delta("heatwave_demand", "uk", "freight_choice", "expedite")
    assert before == -11.8
    assert after == pytest.approx(-57.0)     # the same option, now judged mostly on cost
    assert after != before


def test_a_scenario_that_cares_about_service_scores_expedite_differently(sandbox_templates):
    """The same choice is right or wrong depending on what the scenario is
    about. That is the product thesis applied to KPIs instead of countries."""
    _reweight(sandbox_templates, "heatwave_demand",
              {"cash_position": 0.10, "customer_satisfaction": 0.80, "overhead_cost": 0.10})
    service_led = _delta("heatwave_demand", "uk", "freight_choice", "expedite")
    _reweight(sandbox_templates, "heatwave_demand",
              {"cash_position": 0.10, "customer_satisfaction": 0.10, "overhead_cost": 0.80})
    cost_led = _delta("heatwave_demand", "uk", "freight_choice", "expedite")
    assert service_led > 0 > cost_led


def test_every_weighted_score_shows_its_own_arithmetic():
    """Rule 8: a score must carry its provenance, now per KPI."""
    s = generator.generate("heatwave_demand", "nigeria", seed=1)
    r = scoring.score_decision(s, "freight_choice", "expedite")
    rows = {row["kpi"]: row for row in r["kpi_breakdown"]}
    assert rows["overhead_cost"]["points"] == -84.0          # -40 x Nigeria's 2.1 multiplier
    assert rows["overhead_cost"]["weight"] == 0.25
    assert rows["overhead_cost"]["weighted"] == -21.0
    assert rows["customer_satisfaction"]["weighted"] == pytest.approx(4.2)
    assert round(sum(row["weighted"] for row in r["kpi_breakdown"]), 1) == r["score_delta"]


def test_a_weight_only_matters_where_the_option_has_an_impact(sandbox_templates):
    """Standard freight touches satisfaction only, so a cash-heavy scenario
    leaves it alone. Proves the weighting is per KPI, not a blanket factor."""
    before = _delta("heatwave_demand", "uk", "freight_choice", "standard")
    _reweight(sandbox_templates, "heatwave_demand",
              {"cash_position": 0.90, "customer_satisfaction": 0.05, "overhead_cost": 0.05})
    after = _delta("heatwave_demand", "uk", "freight_choice", "standard")
    assert before == -2.1 and after == pytest.approx(-0.3)


def test_an_impact_on_an_unmeasured_kpi_fails_loud_at_authoring_time():
    bad = {
        "id": "x", "industry": "y", "title": "t", "narrative": "n {{product}}",
        "product_pool": ["a"],
        "decisions": [{"id": "d", "label": "l", "options": ["a", "b"], "scoring": {
            "a": {"impact": {"margin": {"points": 5}}, "reason": "r {delta}"},
            "b": {"impact": {"reputation": {"points": 5}}, "reason": "r {delta}"}}}],
        "kpi_weights": {"margin": 1.0},
    }
    with pytest.raises(templates.InvalidTemplateError, match="'reputation' is not one of this template's KPIs"):
        templates.validate(bad)


def test_an_impact_that_scales_with_an_unknown_rule_fails_loud():
    bad = {
        "id": "x", "industry": "y", "title": "t", "narrative": "n {{product}}",
        "product_pool": ["a"],
        "decisions": [{"id": "d", "label": "l", "options": ["a", "b"], "scoring": {
            "a": {"impact": {"margin": {"points": 5, "scales_with": "moon_phase"}}, "reason": "r {delta}"},
            "b": {"impact": {"margin": {"points": 1}}, "reason": "r {delta}"}}}],
        "kpi_weights": {"margin": 1.0},
    }
    with pytest.raises(templates.InvalidTemplateError, match="scales_with"):
        templates.validate(bad)


def test_an_option_with_neither_impact_nor_points_fails_loud():
    bad = {
        "id": "x", "industry": "y", "title": "t", "narrative": "n {{product}}",
        "product_pool": ["a"],
        "decisions": [{"id": "d", "label": "l", "options": ["a", "b"], "scoring": {
            "a": {"reason": "r"}, "b": {"points": 1, "reason": "r"}}}],
        "kpi_weights": {"margin": 1.0},
    }
    with pytest.raises(templates.InvalidTemplateError, match="impact"):
        templates.validate(bad)


def test_both_shipped_templates_are_weighted_not_legacy():
    """If a shipped template slips back to bare points, the KPIs it declares
    stop mattering and this product is a quiz again."""
    for tid in templates.available():
        tpl = templates.load(tid)
        for d in tpl["decisions"]:
            for opt, rule in d["scoring"].items():
                assert "impact" in rule, f"{tid}.{d['id']}.{opt} still uses unweighted points"


def test_locale_and_kpi_weighting_compose(sandbox_templates):
    """Both dimensions at once: country multiplier inside a weighted KPI."""
    deltas = {l: _delta("heatwave_demand", l, "freight_choice", "expedite") for l in locales.available()}
    assert len(set(deltas.values())) == 4
    _reweight(sandbox_templates, "heatwave_demand",
              {"cash_position": 0.34, "customer_satisfaction": 0.33, "overhead_cost": 0.33})
    after = {l: _delta("heatwave_demand", l, "freight_choice", "expedite") for l in locales.available()}
    assert len(set(after.values())) == 4
    assert all(after[l] != deltas[l] for l in deltas)
