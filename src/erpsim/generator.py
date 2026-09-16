"""Scenario generation: template x locale = scenario. Deterministic per seed
(Rule 3). This function is the whole product thesis in code: adding a
country or an industry never touches this file."""
import random
from . import locales, templates


def generate(template_id: str, locale_code: str, seed: int) -> dict:
    tpl = templates.load(template_id)
    loc = locales.load(locale_code)
    rnd = random.Random(seed)

    product = rnd.choice(tpl["product_pool"])
    narrative = tpl["narrative"].replace("{{product}}", product)

    tax = loc["tax"]
    return {
        "template_id": template_id,
        "locale": loc["code"],
        "seed": seed,
        "title": tpl["title"],
        "narrative": narrative,
        "currency": loc["currency"],
        "decisions": tpl["decisions"],
        "kpi_weights": tpl["kpi_weights"],
        "locale_rules": {
            "tax_type": tax["type"],
            "tax_rate": tax["standard_rate"],
            "tax_notes": tax["notes"],
            "freight_expedite_multiplier": loc["freight_expedite_multiplier"],
            "payment_terms_days": loc["payment_terms_days"],
        },
    }
