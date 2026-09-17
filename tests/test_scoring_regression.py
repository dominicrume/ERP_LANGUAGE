"""Golden-file regression for Fix 2 (scoring moves from Python to YAML).
The fixture was captured from v0.2.0 scoring.py BEFORE the refactor.
Every heatwave_demand score and justification must stay byte-identical."""
import json
from pathlib import Path
from erpsim import generator, scoring

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "heatwave_scores_v0.2.json").read_text())


def test_heatwave_scores_match_v0_2_golden():
    assert len(GOLDEN) == 20  # 4 locales x (2 + 3 options)
    for key, expected in GOLDEN.items():
        loc, decision_id, choice = key.split("|")
        s = generator.generate("heatwave_demand", loc, seed=1)
        assert scoring.score_decision(s, decision_id, choice) == expected, key
