"""Scenario template loader — Rule 2: templates are data, never code.
A template carries its own scoring rules; scoring.py only interprets them."""
from pathlib import Path
from string import Formatter
import yaml

from .locales import LOCALE_RULE_FIELDS

_DIR = Path(__file__).resolve().parents[2] / "config" / "templates"
REQUIRED_KEYS = {"id", "industry", "title", "narrative", "product_pool", "decisions", "kpi_weights"}
REASON_FIELDS = set(LOCALE_RULE_FIELDS) | {"locale", "currency", "choice", "points"}


class UnknownTemplateError(ValueError):
    pass


class InvalidTemplateError(ValueError):
    pass


def available() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.yaml"))


def load(template_id: str) -> dict:
    p = _DIR / f"{template_id}.yaml"
    if not p.exists():
        raise UnknownTemplateError(f"no template '{template_id}'. Available: {available()}")
    data = yaml.safe_load(p.read_text())
    validate(data)
    return data


def _validate_decision(d: dict) -> None:
    for key in ("id", "label", "options", "scoring"):
        if key not in d:
            raise InvalidTemplateError(f"decision is missing '{key}'")
    did = d["id"]
    if not d["options"]:
        raise InvalidTemplateError(f"decision '{did}' must list at least one option")
    if not isinstance(d["scoring"], dict):
        raise InvalidTemplateError(f"decision '{did}': scoring must map each option to a rule")
    missing = set(d["options"]) - set(d["scoring"])
    extra = set(d["scoring"]) - set(d["options"])
    if missing:
        raise InvalidTemplateError(f"decision '{did}': no scoring rule for options {sorted(missing)}")
    if extra:
        raise InvalidTemplateError(f"decision '{did}': scoring rules for unknown options {sorted(extra)}")
    for opt, rule in d["scoring"].items():
        if not isinstance(rule, dict) or not isinstance(rule.get("points"), (int, float)) \
                or isinstance(rule.get("points"), bool):
            raise InvalidTemplateError(f"decision '{did}' option '{opt}': scoring needs numeric 'points'")
        if not isinstance(rule.get("reason"), str) or not rule["reason"].strip():
            raise InvalidTemplateError(f"decision '{did}' option '{opt}': scoring needs a 'reason' string")
        mult = rule.get("multiply_by")
        if mult is not None and mult not in LOCALE_RULE_FIELDS:
            raise InvalidTemplateError(f"decision '{did}' option '{opt}': multiply_by must be one of "
                                       f"{list(LOCALE_RULE_FIELDS)}, got '{mult}'")
        used = {name for _, name, _, _ in Formatter().parse(rule["reason"]) if name}
        unknown = used - REASON_FIELDS
        if unknown:
            raise InvalidTemplateError(f"decision '{did}' option '{opt}': reason references unknown "
                                       f"fields {sorted(unknown)}; allowed: {sorted(REASON_FIELDS)}")


def validate(data: dict) -> None:
    """Rule 7: instructor-authored templates fail loud at authoring time."""
    if not isinstance(data, dict):
        raise InvalidTemplateError("template must be a mapping")
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise InvalidTemplateError(f"template missing required keys: {sorted(missing)}")
    if abs(sum(data["kpi_weights"].values()) - 1.0) > 1e-6:
        raise InvalidTemplateError("kpi_weights must sum to 1.0")
    if not data["decisions"]:
        raise InvalidTemplateError("template must define at least one decision")
    if not data["product_pool"]:
        raise InvalidTemplateError("product_pool must list at least one product")
    for d in data["decisions"]:
        _validate_decision(d)
