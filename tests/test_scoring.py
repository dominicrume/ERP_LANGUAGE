from erpsim import generator, scoring


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
