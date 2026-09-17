"""Decision scoring: a generic interpreter over the template's own rules
(Rule 2: templates are data, never code).

An option states its impact on the KPIs the template says it measures, and
the template's kpi_weights decide how much each KPI counts. That is what
makes this decision-support training rather than a quiz: change a weight in
the YAML and the score moves, with no code change.

    scoring:
      expedite:
        impact:
          overhead_cost:         { points: -40, scales_with: freight_expedite_multiplier }
          customer_satisfaction: { points: 12 }
        reason: "..."

contribution = sum over KPIs of (points x locale multiplier) x kpi_weight

The older form, a bare `points` on the option, still works and contributes
unweighted. It predates KPI weighting and stays supported because an
instructor may already have published a template that uses it.
"""
from typing import Any, Dict

from .locales import LOCALE_RULE_FIELDS


class ScoringError(ValueError):
    """Loud failure: the decision or choice has no rule in this template."""


def _find_decision(scenario: Dict[str, Any], decision_id: str) -> Dict[str, Any]:
    for d in scenario["decisions"]:
        if d["id"] == decision_id:
            return d
    raise ScoringError(f"no decision '{decision_id}' in template '{scenario['template_id']}'")


def _scaled(points: float, field: str | None, rules: Dict[str, Any]) -> float:
    if not field:
        return float(points)
    if field not in LOCALE_RULE_FIELDS:                     # pragma: no cover - validation catches this
        raise ScoringError(f"'{field}' is not a locale rule")
    return float(points) * float(rules[field])


def score_decision(scenario: Dict[str, Any], decision_id: str, choice: str) -> Dict[str, Any]:
    rules = scenario["locale_rules"]
    weights = scenario.get("kpi_weights") or {}
    decision = _find_decision(scenario, decision_id)
    try:
        rule = decision["scoring"][choice]
    except KeyError:
        raise ScoringError(f"choice '{choice}' has no scoring rule for '{decision_id}'. "
                           f"Options: {decision['options']}") from None

    breakdown = []
    if "impact" in rule:
        total = 0.0
        for kpi, effect in rule["impact"].items():
            if kpi not in weights:                          # pragma: no cover - validation catches this
                raise ScoringError(f"'{kpi}' is not a KPI of this template")
            local = _scaled(effect["points"], effect.get("scales_with"), rules)
            weighted = local * float(weights[kpi])
            total += weighted
            breakdown.append({"kpi": kpi, "points": round(local, 1),
                              "weight": float(weights[kpi]), "weighted": round(weighted, 1)})
        points = total
    else:
        # Legacy, unweighted: the option moves the score directly. An
        # unscaled value keeps its own type, so an older reason written as
        # "{points:+d}" still formats.
        points = (_scaled(rule["points"], rule["multiply_by"], rules)
                  if rule.get("multiply_by") else rule["points"])

    ctx = {**rules, "locale": scenario["locale"], "currency": scenario["currency"],
           "choice": choice, "points": points,
           # Pre-formatted so authored reasons need no format specs:
           "delta": f"{points:+.1f}" if isinstance(points, float) else f"{points:+d}",
           "tax_percent": f"{rules['tax_rate'] * 100:.1f}%"}
    justification = [rule["reason"].format(**ctx)]
    justification.append(
        f"Reminder: {rules['tax_type']} at {rules['tax_rate']*100:.1f}% "
        f"applies to this transaction in {scenario['locale']}. {rules['tax_notes']}"
    )

    return {"decision_id": decision_id, "choice": choice,
            "score_delta": round(points, 1),
            "running_score": round(100.0 + points, 1),   # deprecated: use a run's score_so_far
            "kpi_breakdown": breakdown,
            "justification": justification}
