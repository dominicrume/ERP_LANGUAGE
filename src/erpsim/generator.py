"""Scenario generation: template x locale = scenario. Deterministic per seed
(Rule 3). This function is the whole product thesis in code: adding a
country or an industry never touches this file."""
import random
from . import locales, templates


def generate(template_id: str, locale_code: str, seed: int) -> dict:
    return generate_from(templates.load(template_id), locales.load(locale_code), seed,
                         template_id=template_id, locale_id=locale_code.lower())


def generate_from(tpl: dict, loc: dict, seed: int, template_id: str | None = None,
                  locale_id: str | None = None) -> dict:
    """Same engine, but for a template/locale already in memory — used by the
    instructor preview on an unsaved draft. Output is identical to generate()."""
    rnd = random.Random(seed)

    product = rnd.choice(tpl["product_pool"])
    narrative = tpl["narrative"].replace("{{product}}", product)

    return {
        "template_id": template_id or tpl["id"],
        "locale": loc["code"],                                   # display code (UK, BR, DE, NG)
        "locale_id": locale_id or _locale_id_for(loc),           # the identifier the API accepts
        "seed": seed,
        "title": tpl["title"],
        "narrative": narrative,
        "currency": loc["currency"],
        "decisions": tpl["decisions"],
        "kpi_weights": tpl["kpi_weights"],
        "locale_rules": locales.rules(loc),
    }


def _locale_id_for(loc: dict) -> str:
    """Recover the file stem for a loaded locale dict (preview path only)."""
    for lid in locales.available():
        if locales.load(lid) is loc or locales.load(lid) == loc:
            return lid
    return loc["code"].lower()
