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

    return {
        "template_id": template_id,
        "locale": loc["code"],              # display code (UK, BR, DE, NG)
        "locale_id": locale_code.lower(),   # the identifier the API accepts
        "seed": seed,
        "title": tpl["title"],
        "narrative": narrative,
        "currency": loc["currency"],
        "decisions": tpl["decisions"],
        "kpi_weights": tpl["kpi_weights"],
        "locale_rules": locales.rules(loc),
    }
