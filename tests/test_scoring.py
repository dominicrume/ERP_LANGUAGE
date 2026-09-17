import pytest
from erpsim import generator, scoring, templates, locales


def test_expedite_freight_penalty_differs_by_locale():
    """Same decision, same template — different score because the freight
    multiplier differs by country. This IS the localization thesis."""
    uk = generator.generate("heatwave_demand", "uk", seed=1)
    br = generator.generate("heatwave_demand", "brazil", seed=1)
    uk_score = scoring.score_decision(uk, "freight_choice", "expedite")
    br_score = scoring.score_decision(br, "freight_choice", "expedite")
    assert uk_score["score_delta"] != br_score["score_delta"]


def test_every_score_carries_justification():
    s = generator.generate("heatwave_demand", "uk", seed=1)
    r = scoring.score_decision(s, "customer_allocation", "highest_value_first")
    assert r["justification"]  # provenance, Rule 8


def test_standard_freight_no_penalty():
    s = generator.generate("heatwave_demand", "germany", seed=1)
    r = scoring.score_decision(s, "freight_choice", "standard")
    assert r["score_delta"] == 0


def test_every_option_of_every_template_scores_with_a_reason():
    """Fix 2: no decision may fall through to a silent zero. Every option in
    every shipped template x locale must produce a specific justification
    line, not just the generic tax reminder."""
    for t in templates.available():
        for l in locales.available():
            s = generator.generate(t, l, seed=1)
            for d in s["decisions"]:
                for opt in d["options"]:
                    r = scoring.score_decision(s, d["id"], opt)
                    assert len(r["justification"]) == 2, (t, l, d["id"], opt)
                    assert "Reminder:" not in r["justification"][0]


def test_made_to_order_subcontract_is_locale_aware():
    uk = generator.generate("made_to_order", "uk", seed=1)
    ng = generator.generate("made_to_order", "nigeria", seed=1)
    assert scoring.score_decision(uk, "subcontract", "yes")["score_delta"] != \
           scoring.score_decision(ng, "subcontract", "yes")["score_delta"]


def test_unknown_decision_fails_loud():
    s = generator.generate("heatwave_demand", "uk", seed=1)
    with pytest.raises(scoring.ScoringError):
        scoring.score_decision(s, "not_a_decision", "x")


def test_unknown_choice_fails_loud():
    s = generator.generate("heatwave_demand", "uk", seed=1)
    with pytest.raises(scoring.ScoringError, match="TELEPORT"):
        scoring.score_decision(s, "freight_choice", "TELEPORT")
