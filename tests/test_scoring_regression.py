"""Two goldens, because the scoring model changed on purpose in v1.0.

`heatwave_scores_v0.2_legacy.json` pins the old unweighted `points` form,
which is still supported for templates published before KPI weighting, and
is checked against a frozen copy of the v0.2 template.

`weighted_scores_v1.json` pins the shipped templates under KPI weighting.
Neither file may be edited to make a test pass: if a number here moves, the
scenario a learner played yesterday scores differently today, and that has
to be a deliberate, changelogged decision.
"""
import json
from pathlib import Path

import yaml

from erpsim import generator, locales, scoring, templates

FIXTURES = Path(__file__).parent / "fixtures"
LEGACY_GOLDEN = json.loads((FIXTURES / "heatwave_scores_v0.2_legacy.json").read_text())
LEGACY_TEMPLATE = yaml.safe_load((FIXTURES / "heatwave_v0.2_legacy.yaml").read_text())
WEIGHTED_GOLDEN = json.loads((FIXTURES / "weighted_scores_v1.json").read_text())


def test_the_legacy_unweighted_points_form_still_scores_exactly_as_it_did():
    assert len(LEGACY_GOLDEN) == 20
    templates.validate(LEGACY_TEMPLATE)          # still a publishable template
    for key, expected in LEGACY_GOLDEN.items():
        loc, decision_id, choice = key.split("|")
        s = generator.generate_from(LEGACY_TEMPLATE, locales.load(loc), 1,
                                    template_id="heatwave_demand", locale_id=loc)
        got = scoring.score_decision(s, decision_id, choice)
        assert got["score_delta"] == expected["score_delta"], key
        assert got["justification"] == expected["justification"], key
        assert got["kpi_breakdown"] == [], "the legacy form has no KPI breakdown"


def test_the_shipped_templates_match_the_v1_weighted_golden():
    assert len(WEIGHTED_GOLDEN) == 40
    for key, expected in WEIGHTED_GOLDEN.items():
        template_id, loc, decision_id, choice = key.split("|")
        s = generator.generate(template_id, loc, seed=1)
        got = scoring.score_decision(s, decision_id, choice)
        assert got["score_delta"] == expected["score_delta"], key
        assert got["kpi_breakdown"] == expected["kpi_breakdown"], key
        assert got["justification"] == expected["justification"], key
