"""Scenario template loader — Rule 2: templates are data, never code.
A template carries its own scoring rules; scoring.py only interprets them."""
import logging
import re
from pathlib import Path
from string import Formatter
import yaml

from .locales import LOCALE_RULE_FIELDS

log = logging.getLogger("erpsim.templates")
_DIR = Path(__file__).resolve().parents[2] / "config" / "templates"
REQUIRED_KEYS = {"id", "industry", "title", "narrative", "product_pool", "decisions", "kpi_weights"}
REASON_FIELDS = set(LOCALE_RULE_FIELDS) | {"locale", "currency", "choice", "points"}


class UnknownTemplateError(ValueError):
    pass


class InvalidTemplateError(ValueError):
    pass


class UnloadableTemplateError(UnknownTemplateError):
    """The file exists but is not valid YAML or fails validation. Subclass of
    UnknownTemplateError so the API treats it as 'not available' (404) for
    that template only — the rest of the catalog keeps working."""


def _load_file(p: Path) -> dict:
    try:
        data = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise UnloadableTemplateError(f"template file {p.name} is not valid YAML: {e}") from None
    try:
        validate(data)
    except InvalidTemplateError as e:
        raise UnloadableTemplateError(f"template file {p.name} is invalid: {e}") from None
    return data


def available() -> list[str]:
    """Templates that actually load. A broken file is logged and skipped."""
    out = []
    for p in sorted(_DIR.glob("*.yaml")):
        try:
            _load_file(p)
        except UnloadableTemplateError as e:
            log.warning("skipping template %s: %s", p.name, e)
            continue
        out.append(p.stem)
    return out


ID_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")


def load(template_id: str) -> dict:
    if not ID_PATTERN.match(template_id):
        raise UnknownTemplateError(f"template id must match {ID_PATTERN.pattern}. Available: {available()}")
    p = _DIR / f"{template_id}.yaml"
    if not p.exists():
        raise UnknownTemplateError(f"no template '{template_id}'. Available: {available()}")
    return _load_file(p)


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
