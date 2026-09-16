"""Decision scoring — locale-aware. The SAME decision scores differently
under different tax/freight rules (Rule 8: justification always stored)."""
from typing import Any, Dict


def score_decision(scenario: Dict[str, Any], decision_id: str, choice: str) -> Dict[str, Any]:
    rules = scenario["locale_rules"]
    base = 100.0
    justification = []

    if decision_id == "freight_choice":
        if choice == "expedite":
            penalty = 20 * rules["freight_expedite_multiplier"]
            base -= penalty
            justification.append(
                f"Expedite freight in {scenario['locale']} carries a "
                f"{rules['freight_expedite_multiplier']}x cost multiplier: -{penalty:.1f} pts."
            )
        else:
            justification.append("Standard freight: no premium applied.")

    if decision_id == "customer_allocation":
        bonus = {"highest_value_first": 8, "strategic_accounts_first": 5,
                 "first_come_first_served": 0}.get(choice, 0)
        base += bonus
        justification.append(f"'{choice}' allocation: {'+' if bonus>=0 else ''}{bonus} pts vs. baseline.")

    tax_note = (f"Reminder: {rules['tax_type']} at {rules['tax_rate']*100:.1f}% "
                f"applies to this transaction in {scenario['locale']}. {rules['tax_notes']}")
    justification.append(tax_note)

    return {"decision_id": decision_id, "choice": choice, "score_delta": round(base - 100.0, 1),
            "running_score": round(base, 1), "justification": justification}
