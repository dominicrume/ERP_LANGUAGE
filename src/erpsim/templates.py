"""Scenario template loader — Rule 2: templates are data, never code."""
from pathlib import Path
import yaml

_DIR = Path(__file__).resolve().parents[2] / "config" / "templates"
REQUIRED_KEYS = {"id", "industry", "title", "narrative", "product_pool", "decisions", "kpi_weights"}


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


def validate(data: dict) -> None:
    """Rule 7: instructor-authored templates fail loud at authoring time."""
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise InvalidTemplateError(f"template missing required keys: {sorted(missing)}")
    if abs(sum(data["kpi_weights"].values()) - 1.0) > 1e-6:
        raise InvalidTemplateError("kpi_weights must sum to 1.0")
    if not data["decisions"]:
        raise InvalidTemplateError("template must define at least one decision")
