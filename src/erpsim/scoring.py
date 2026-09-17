"""Decision scoring — a generic interpreter over the template's own scoring
rules (Rule 2: templates are data, never code). The SAME choice scores
differently under different locales because a rule may multiply its points
by a locale_rules field. Every result carries its justification (Rule 8)."""
from typing import Any, Dict


class ScoringError(ValueError):
    """Loud failure: the decision or choice has no rule in this template."""


def _find_decision(scenario: Dict[str, Any], decision_id: str) -> Dict[str, Any]:
    for d in scenario["decisions"]:
        if d["id"] == decision_id:
            return d
    raise ScoringError(f"no decision '{decision_id}' in template '{scenario['template_id']}'")


def score_decision(scenario: Dict[str, Any], decision_id: str, choice: str) -> Dict[str, Any]:
    rules = scenario["locale_rules"]
    decision = _find_decision(scenario, decision_id)
    try:
        rule = decision["scoring"][choice]
    except KeyError:
        raise ScoringError(f"choice '{choice}' has no scoring rule for '{decision_id}'. "
                           f"Options: {decision['options']}") from None

    points = rule["points"]
    if rule.get("multiply_by"):
        points = points * rules[rule["multiply_by"]]

    ctx = {**rules, "locale": scenario["locale"], "currency": scenario["currency"],
           "choice": choice, "points": points}
    justification = [rule["reason"].format(**ctx)]
    justification.append(
        f"Reminder: {rules['tax_type']} at {rules['tax_rate']*100:.1f}% "
        f"applies to this transaction in {scenario['locale']}. {rules['tax_notes']}"
    )

    base = 100.0 + points
    return {"decision_id": decision_id, "choice": choice, "score_delta": round(base - 100.0, 1),
            "running_score": round(base, 1), "justification": justification}
